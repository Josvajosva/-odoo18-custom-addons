/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    /**
     * Override pointsForPrograms to apply floor-based point calculation
     * for programs that have use_floor_points enabled.
     */
    pointsForPrograms(programs) {
        const result = super.pointsForPrograms(programs);

        for (const program of programs) {
            if (!program.use_floor_points && !program.double_points_days) {
                continue;
            }
            if (!result[program.id] || result[program.id].length === 0) {
                continue;
            }

            // Recalculate floor-based points for money mode rules
            if (program.use_floor_points) {
                const floorPoints = this._calculateFloorPoints(program);
                if (floorPoints !== null) {
                    result[program.id][0].points = floorPoints;
                }
            }

            // Apply repeat-purchase doubling
            // Note: We only apply doubling on the backend (Python) since we need DB access
            // to check recent purchases. The POS frontend shows base floor points.
            // The actual doubling happens in confirm_coupon_programs on the server.
        }
        return result;
    },

    /**
     * Calculate floor-based points for money mode rules.
     * floor(amount_paid / minimum_amount) * reward_point_amount
     */
    _calculateFloorPoints(program) {
        const orderLines = this.get_orderlines().filter(
            (line) => !line.is_reward_line && !line.combo_parent_id
        );
        let hasMoneyRule = false;
        let totalPoints = 0;

        for (const rule of program.rule_ids) {
            if (rule.reward_point_mode !== "money") {
                continue;
            }
            hasMoneyRule = true;

            const minimumAmount = rule.minimum_amount;
            if (minimumAmount <= 0) {
                continue;
            }

            // Calculate amount paid for matching products
            let amountPaid = 0;
            for (const line of orderLines) {
                if (line.combo_parent_id) {
                    continue;
                }
                if (
                    rule.any_product ||
                    rule.validProductIds.has(line.product_id.id)
                ) {
                    amountPaid += line.combo_line_ids.length > 0
                        ? line.getComboTotalPrice()
                        : line.get_price_with_tax();
                }
            }

            // Check minimum amount condition
            let amountCheck = amountPaid;
            if (rule.minimum_amount_tax_mode === "excl") {
                amountCheck = 0;
                for (const line of orderLines) {
                    if (line.combo_parent_id) {
                        continue;
                    }
                    if (
                        rule.any_product ||
                        rule.validProductIds.has(line.product_id.id)
                    ) {
                        amountCheck += line.combo_line_ids.length > 0
                            ? line.getComboTotalPriceWithoutTax()
                            : line.get_price_without_tax();
                    }
                }
            }

            if (minimumAmount > amountCheck) {
                continue;
            }

            // Floor-based calculation
            const multiples = Math.floor(amountPaid / minimumAmount);
            totalPoints += multiples * rule.reward_point_amount;
        }

        if (hasMoneyRule) {
            return Math.round(totalPoints * 100) / 100;
        }
        return null;
    },
});