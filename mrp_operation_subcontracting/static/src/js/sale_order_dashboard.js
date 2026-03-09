// static/src/js/sale_order_mrp_dashboard.js
odoo.define('mrp_operation_subcontracting.sale_order_mrp_dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');

    var SaleOrderDashboard = AbstractAction.extend({
        template: 'template_sale_order_mrp_dashboard',

        start: function () {
            var self = this;
            return rpc.query({
                model: 'sale.order',
                method: 'get_mrp_status_counts',
            }).then(function (result) {
                self.$el.find('.view-sale-orders').each(function () {
                    var $btn = $(this);
                    var status = $btn.data('status');
                    $btn.text(`${result[status]} To Process`);
                });

                self.$el.on('click', '.view-sale-orders', function () {
                    var status = $(this).data('status');
                    self.do_action({
                        name: 'Sale Orders - ' + status,
                        type: 'ir.actions.act_window',
                        res_model: 'sale.order',
                        view_mode: 'tree,form',
                        domain: [['mrp_status', '=', status]],
                        views: [[false, 'tree'], [false, 'form']],
                    });
                });
            });
        }
    });

    core.action_registry.add('sale_order_mrp_status_dashboard', SaleOrderDashboard);

    return SaleOrderDashboard;
});
