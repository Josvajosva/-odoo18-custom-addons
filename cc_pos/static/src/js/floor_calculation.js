/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { roundPrecision } from "@web/core/utils/numbers";

console.log('ffffffffffffffffffffff')

//patch(PosOrder.prototype, {
//    pointsForPrograms(programs) {
//        const result = super.pointsForPrograms(programs);
//
//        for (const program of programs) {
//            // Check if any rule has floor_calculation enabled
//            const hasFloorRule = program.rule_ids.some((r) => r.floor_calculation);
//            if (!hasFloorRule) {
//                continue;
//            }
//            if (!result[program.id] || result[program.id].length === 0) {
//                continue;
//            }
//
//            // Recalculate points for this program with floor logic per rule
//            const orderLines = this.get_orderlines().filter(
//                (line) => !line.combo_parent_id
//            );
//            let totalPoints = 0;
//
//            for (const rule of program.rule_ids) {
//                if (rule.mode === "with_code" &&
//                    !this.uiState.codeActivatedProgramRules.includes(rule.id)) {
//                    continue;
//                }
//
//                // Get matching lines for this rule
//                const linesForRule = orderLines.filter(
//                    (line) => !line.is_reward_line &&
//                        (rule.any_product || rule.validProductIds.has(line.product_id.id))
//                );
//
//                // Calculate amounts
//                const amountWithTax = linesForRule.reduce(
//                    (sum, line) => sum + (line.combo_line_ids.length > 0
//                        ? line.getComboTotalPrice()
//                        : line.get_price_with_tax()),
//                    0
//                );
//                const amountWithoutTax = linesForRule.reduce(
//                    (sum, line) => sum + (line.combo_line_ids.length > 0
//                        ? line.getComboTotalPriceWithoutTax()
//                        : line.get_price_without_tax()),
//                    0
//                );
//                const amountCheck = rule.minimum_amount_tax_mode === "incl"
//                    ? amountWithTax : amountWithoutTax;
//
//                // Check minimum amount
//                if (rule.minimum_amount > amountCheck) {
//                    continue;
//                }
//
//                // Check minimum quantity
//                const totalQty = linesForRule.reduce(
//                    (sum, line) => sum + line.get_quantity(), 0
//                );
//                if (totalQty < rule.minimum_qty) {
//                    continue;
//                }
//
//                // Calculate paid amount (including reward lines from other programs)
//                let orderedProductPaid = 0;
//                for (const line of orderLines) {
//                    if (
//                        ((!line.reward_product_id &&
//                            (rule.any_product || rule.validProductIds.has(line.product_id.id))) ||
//                            (line.reward_product_id &&
//                                (rule.any_product ||
//                                    rule.validProductIds.has(line._reward_product_id?.id)))) &&
//                        !line.ignoreLoyaltyPoints({ program })
//                    ) {
//                        if (line.is_reward_line) {
//                            const reward = line.reward_id;
//                            if (
//                                program.id === reward.program_id.id ||
//                                ["gift_card", "ewallet"].includes(reward.program_id.program_type)
//                            ) {
//                                continue;
//                            }
//                        }
//                        orderedProductPaid += line.combo_line_ids.length > 0
//                            ? line.getComboTotalPrice()
//                            : line.get_price_with_tax();
//                    }
//                }
//
//                // Calculate points for this rule
//                let rulePoints = 0;
//                if (rule.reward_point_mode === "order") {
//                    rulePoints = rule.reward_point_amount;
//                } else if (rule.reward_point_mode === "money") {
//                    rulePoints = roundPrecision(
//                        rule.reward_point_amount * orderedProductPaid, 0.01
//                    );
//                } else if (rule.reward_point_mode === "unit") {
//                    rulePoints = rule.reward_point_amount * totalQty;
//                }
//
//                if (rule.floor_calculation === true) {
//                    const blockSize = 100;
//                    const completedBlocks = Math.floor(orderedProductPaid / blockSize);
//                    rulePoints = completedBlocks * blockSize * rule.reward_point_amount;
//                    console.log(rulePoints, 'aaaaaaaaaaaaaaaaaaaaaaaaa')
//                }
//                totalPoints += rulePoints;
//            }
//
//            // Replace points with recalculated value
//            result[program.id][0].points = totalPoints;
//        }
//        return result;
//    },
//});