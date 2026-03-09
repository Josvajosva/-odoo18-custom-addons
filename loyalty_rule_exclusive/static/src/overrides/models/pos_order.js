/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { roundPrecision } from "@web/core/utils/numbers";

/**
 * Track which rules were applied for exclusive evaluation.
 * This is used for logging and debugging purposes.
 */
let exclusiveRuleApplied = {};

patch(PosOrder.prototype, {
    /**
     * Override pointsForPrograms to implement exclusive rule evaluation.
     * 
     * When a program has `exclusive_rule_evaluation` enabled:
     * - Rules are sorted by minimum_amount (descending) - higher threshold first
     * - Only the FIRST matching rule is applied
     * - Other rules are skipped even if they would match
     * 
     * This ensures mutually exclusive rule application:
     * - Order < 50 → Only lower threshold rule applies
     * - Order >= 50 → Only higher threshold rule applies (not both)
     *
     * @param {Array} programs list of loyalty.program
     * @returns {Object} Containing the points gained per program
     */
    pointsForPrograms(programs) {
        // Reset tracking for this calculation
        exclusiveRuleApplied = {};
        
        const orderLines = this.get_orderlines();
        const linesPerRule = {};
        
        // Build lines per rule mapping (same as original)
        for (const line of orderLines) {
            const reward = line.reward_id;
            const isDiscount = reward && reward.reward_type === "discount";
            const rewardProgram = reward && reward.program_id;
            
            if (isDiscount && rewardProgram.trigger === "auto") {
                continue;
            }
            if (!this.isLineValidForLoyaltyPoints(line)) {
                continue;
            }
            for (const program of programs) {
                if (isDiscount && rewardProgram.id === program.id) {
                    continue;
                }
                for (const rule of program.rule_ids) {
                    if (rule.any_product || rule.validProductIds.has(line.product_id.id)) {
                        if (!linesPerRule[rule.id]) {
                            linesPerRule[rule.id] = [];
                        }
                        linesPerRule[rule.id].push(line);
                    }
                }
            }
        }

        const result = {};
        
        for (const program of programs) {
            // Check if exclusive rule evaluation is enabled for this program
            const useExclusive = program.exclusive_rule_evaluation;
            
            if (useExclusive) {
                // Use exclusive rule evaluation logic
                result[program.id] = this._computePointsExclusiveRules(
                    program, orderLines, linesPerRule
                );
            } else {
                // Use standard logic
                result[program.id] = this._computePointsStandardRules(
                    program, orderLines, linesPerRule
                );
            }
        }
        
        return result;
    },

    /**
     * Sort rules for exclusive evaluation.
     * 
     * Rules are sorted by minimum_amount descending (higher threshold first).
     * This ensures that more specific rules (higher thresholds) are evaluated
     * first, preventing lower threshold rules from matching when a higher
     * threshold rule should apply.
     *
     * @param {Array} rules - Array of rule objects
     * @returns {Array} Sorted array of rules
     */
    _getSortedRulesForExclusiveEvaluation(rules) {
        return [...rules].sort((a, b) => {
            // Sort by minimum_amount descending (higher amount first)
            return b.minimum_amount - a.minimum_amount;
        });
    },

    /**
     * Compute points with exclusive rule evaluation.
     * Only the first matching rule (sorted by minimum_amount descending) is applied.
     *
     * @param {Object} program - loyalty.program object
     * @param {Array} orderLines - Order lines
     * @param {Object} linesPerRule - Lines mapped per rule ID
     * @returns {Array} Points result array
     */
    _computePointsExclusiveRules(program, orderLines, linesPerRule) {
        let points = 0;
        const splitPoints = [];
        
        // Sort rules by minimum_amount descending (higher threshold first)
        const sortedRules = this._getSortedRulesForExclusiveEvaluation(program.rule_ids);
        
        console.log(
            `=== Exclusive Rule Evaluation for Program '${program.name}' (ID: ${program.id}) ===`
        );
        console.log(`Order Total: ${this.get_total_with_tax()}`);
        console.log(`Evaluating ${sortedRules.length} rules (sorted by min_amount desc)...`);
        
        let appliedRule = null;
        
        for (const rule of sortedRules) {
            // Skip code-activated rules that aren't activated
            if (
                rule.mode === "with_code" &&
                !this.uiState.codeActivatedProgramRules.includes(rule.id)
            ) {
                console.log(
                    `  Rule ${rule.id} (min=${rule.minimum_amount}) skipped: requires code activation`
                );
                continue;
            }
            
            const linesForRule = linesPerRule[rule.id] ? linesPerRule[rule.id] : [];
            const amountWithTax = linesForRule.reduce(
                (sum, line) => sum + line.get_price_with_tax(), 0
            );
            const amountWithoutTax = linesForRule.reduce(
                (sum, line) => sum + line.get_price_without_tax(), 0
            );
            const amountCheck = (rule.minimum_amount_tax_mode === "incl" && amountWithTax) || amountWithoutTax;
            
            console.log(
                `  Checking Rule ${rule.id}: min_amount=${rule.minimum_amount}, order_amount=${amountCheck}`
            );
            
            // Check minimum amount threshold
            if (rule.minimum_amount > amountCheck) {
                console.log(
                    `    → Rule ${rule.id}: SKIPPED (amount ${amountCheck} < minimum ${rule.minimum_amount})`
                );
                continue;
            }
            
            // Check product quantity requirements
            let totalProductQty = 0;
            const qtyPerProduct = {};
            let orderedProductPaid = 0;
            
            for (const line of orderLines) {
                if (
                    ((!line.reward_product_id &&
                        (rule.any_product || rule.validProductIds.has(line.product_id.id))) ||
                        (line.reward_product_id &&
                            (rule.any_product ||
                                rule.validProductIds.has(line._reward_product_id?.id)))) &&
                    !line.ignoreLoyaltyPoints({ program })
                ) {
                    if (line.is_reward_line) {
                        const reward = line.reward_id;
                        if (
                            program.id === reward.program_id.id ||
                            ["gift_card", "ewallet"].includes(reward.program_id.program_type)
                        ) {
                            continue;
                        }
                    }
                    const lineQty = line._reward_product_id
                        ? -line.get_quantity()
                        : line.get_quantity();
                    if (qtyPerProduct[line._reward_product_id || line.get_product().id]) {
                        qtyPerProduct[line._reward_product_id || line.get_product().id] += lineQty;
                    } else {
                        qtyPerProduct[line._reward_product_id?.id || line.get_product().id] = lineQty;
                    }
                    orderedProductPaid += line.get_price_with_tax();
                    if (!line.is_reward_line) {
                        totalProductQty += lineQty;
                    }
                }
            }
            
            if (totalProductQty < rule.minimum_qty) {
                console.log(
                    `    → Rule ${rule.id}: SKIPPED (qty ${totalProductQty} < minimum ${rule.minimum_qty})`
                );
                continue;
            }
            
            // This rule matches! Since we're in exclusive mode, apply only this rule
            appliedRule = rule;
            
            console.log(`    ★ Rule ${rule.id}: MATCHED AND APPLIED (exclusive mode)`);
            
            // Track which rule was applied
            exclusiveRuleApplied[program.id] = {
                rule_id: rule.id,
                minimum_amount: rule.minimum_amount
            };
            
            // Calculate points for this rule
            if (
                program.applies_on === "future" &&
                rule.reward_point_split &&
                rule.reward_point_mode !== "order"
            ) {
                if (rule.reward_point_mode === "unit") {
                    splitPoints.push(
                        ...Array.apply(null, Array(Math.floor(totalProductQty))).map(() => ({
                            points: rule.reward_point_amount,
                        }))
                    );
                } else if (rule.reward_point_mode === "money") {
                    for (const line of orderLines) {
                        if (
                            line.is_reward_line ||
                            !rule.validProductIds.has(line.product_id.id) ||
                            line.get_quantity() <= 0 ||
                            line.ignoreLoyaltyPoints({ program })
                        ) {
                            continue;
                        }
                        const pointsPerUnit = roundPrecision(
                            (rule.reward_point_amount * line.get_price_with_tax()) /
                                line.get_quantity(),
                            0.01
                        );
                        if (pointsPerUnit > 0) {
                            splitPoints.push(
                                ...Array.apply(null, Array(line.get_quantity())).map(() => {
                                    if (line._gift_barcode && line.get_quantity() == 1) {
                                        return {
                                            points: pointsPerUnit,
                                            barcode: line._gift_barcode,
                                            giftCardId: line._gift_card_id.id,
                                        };
                                    }
                                    return { points: pointsPerUnit };
                                })
                            );
                        }
                    }
                }
            } else {
                if (rule.reward_point_mode === "order") {
                    points = rule.reward_point_amount;
                } else if (rule.reward_point_mode === "money") {
                    points = roundPrecision(
                        rule.reward_point_amount * orderedProductPaid,
                        0.01
                    );
                } else if (rule.reward_point_mode === "unit") {
                    points = rule.reward_point_amount * totalProductQty;
                }
            }
            
            console.log(`    → Rule ${rule.id}: Awarded ${points} points (mode: ${rule.reward_point_mode})`);
            
            // IMPORTANT: Break after first matching rule in exclusive mode
            break;
        }
        
        // Final logging summary
        if (appliedRule) {
            console.log(
                `=== RESULT: Rule ${appliedRule.id} applied exclusively (min_amount=${appliedRule.minimum_amount}) ===`
            );
        } else {
            console.log(`=== RESULT: No rules matched for program '${program.name}' ===`);
        }
        
        const res = points || program.program_type === "coupons" ? [{ points }] : [];
        if (splitPoints.length) {
            res.push(...splitPoints);
        }
        
        // Add applied rules for tracking (for _getPointsCorrection compatibility)
        if (res.length > 0 && appliedRule) {
            res[0].appliedRules = [appliedRule.id];
        }
        
        return res;
    },

    /**
     * Compute points with standard (non-exclusive) rule evaluation.
     * All matching rules contribute their points.
     *
     * This is the original logic moved into a separate method.
     *
     * @param {Object} program - loyalty.program object
     * @param {Array} orderLines - Order lines
     * @param {Object} linesPerRule - Lines mapped per rule ID
     * @returns {Array} Points result array
     */
    _computePointsStandardRules(program, orderLines, linesPerRule) {
        let points = 0;
        const splitPoints = [];
        
        for (const rule of program.rule_ids) {
            if (
                rule.mode === "with_code" &&
                !this.uiState.codeActivatedProgramRules.includes(rule.id)
            ) {
                continue;
            }
            
            const linesForRule = linesPerRule[rule.id] ? linesPerRule[rule.id] : [];
            const amountWithTax = linesForRule.reduce(
                (sum, line) => sum + line.get_price_with_tax(), 0
            );
            const amountWithoutTax = linesForRule.reduce(
                (sum, line) => sum + line.get_price_without_tax(), 0
            );
            const amountCheck = (rule.minimum_amount_tax_mode === "incl" && amountWithTax) || amountWithoutTax;
            
            if (rule.minimum_amount > amountCheck) {
                continue;
            }
            
            let totalProductQty = 0;
            const qtyPerProduct = {};
            let orderedProductPaid = 0;
            
            for (const line of orderLines) {
                if (
                    ((!line.reward_product_id &&
                        (rule.any_product || rule.validProductIds.has(line.product_id.id))) ||
                        (line.reward_product_id &&
                            (rule.any_product ||
                                rule.validProductIds.has(line._reward_product_id?.id)))) &&
                    !line.ignoreLoyaltyPoints({ program })
                ) {
                    if (line.is_reward_line) {
                        const reward = line.reward_id;
                        if (
                            program.id === reward.program_id.id ||
                            ["gift_card", "ewallet"].includes(reward.program_id.program_type)
                        ) {
                            continue;
                        }
                    }
                    const lineQty = line._reward_product_id
                        ? -line.get_quantity()
                        : line.get_quantity();
                    if (qtyPerProduct[line._reward_product_id || line.get_product().id]) {
                        qtyPerProduct[line._reward_product_id || line.get_product().id] += lineQty;
                    } else {
                        qtyPerProduct[line._reward_product_id?.id || line.get_product().id] = lineQty;
                    }
                    orderedProductPaid += line.get_price_with_tax();
                    if (!line.is_reward_line) {
                        totalProductQty += lineQty;
                    }
                }
            }
            
            if (totalProductQty < rule.minimum_qty) {
                continue;
            }
            
            // Calculate points for this rule
            if (
                program.applies_on === "future" &&
                rule.reward_point_split &&
                rule.reward_point_mode !== "order"
            ) {
                if (rule.reward_point_mode === "unit") {
                    splitPoints.push(
                        ...Array.apply(null, Array(Math.floor(totalProductQty))).map(() => ({
                            points: rule.reward_point_amount,
                        }))
                    );
                } else if (rule.reward_point_mode === "money") {
                    for (const line of orderLines) {
                        if (
                            line.is_reward_line ||
                            !rule.validProductIds.has(line.product_id.id) ||
                            line.get_quantity() <= 0 ||
                            line.ignoreLoyaltyPoints({ program })
                        ) {
                            continue;
                        }
                        const pointsPerUnit = roundPrecision(
                            (rule.reward_point_amount * line.get_price_with_tax()) /
                                line.get_quantity(),
                            0.01
                        );
                        if (pointsPerUnit > 0) {
                            splitPoints.push(
                                ...Array.apply(null, Array(line.get_quantity())).map(() => {
                                    if (line._gift_barcode && line.get_quantity() == 1) {
                                        return {
                                            points: pointsPerUnit,
                                            barcode: line._gift_barcode,
                                            giftCardId: line._gift_card_id.id,
                                        };
                                    }
                                    return { points: pointsPerUnit };
                                })
                            );
                        }
                    }
                }
            } else {
                if (rule.reward_point_mode === "order") {
                    points += rule.reward_point_amount;
                } else if (rule.reward_point_mode === "money") {
                    points += roundPrecision(
                        rule.reward_point_amount * orderedProductPaid,
                        0.01
                    );
                } else if (rule.reward_point_mode === "unit") {
                    points += rule.reward_point_amount * totalProductQty;
                }
            }
        }
        
        const res = points || program.program_type === "coupons" ? [{ points }] : [];
        if (splitPoints.length) {
            res.push(...splitPoints);
        }
        return res;
    },
});
