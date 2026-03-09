import { OrderReceipt as BaseOrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

BaseOrderReceipt.template = "hgp_pos.OrderReceipt";
patch(BaseOrderReceipt.prototype, {
    formatToInt(value) {
        return Number(value) || 0;
    },
});

patch(PosOrderline.prototype, {
    setup(vals) {
        this.compare_value = this.compare_value || "";
        this.c_value = this.compare_value || "";
        return super.setup(...arguments);
    },
    getComparePrice() {
        return Number(this.compare_value) || this.get_display_price();
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            compare_value: this.getComparePrice(),
            c_value: formatCurrency(this.getComparePrice(), this.currency),
        };
    },
});
