# -*- coding: utf-8 -*-

import logging
from odoo import models
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class GeneralLedgerHandlerExt(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"

    # ---------------------------------------------------------
    # Register extra SQL fields
    # ---------------------------------------------------------
    def _get_query_amls_additional_fields(self):
        return super()._get_query_amls_additional_fields() + [
            "voucher_no",
            "voucher_type",
            "invoice_no",
            "payment_ref",
            "gstin",
        ]

    # ---------------------------------------------------------
    # Inject fields into AML SQL
    # ---------------------------------------------------------
    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):

        base_query = super()._get_query_amls(
            report,
            options,
            expanded_account_ids,
            offset=offset,
            limit=limit
        )

        return SQL("""
            SELECT
                q.*,
                move.name            AS voucher_no,
                move.move_type       AS voucher_type,
                move.ref             AS invoice_no,
                move.payment_reference AS payment_ref,
                partner.vat          AS gstin
            FROM (%s) q
            LEFT JOIN account_move move   ON move.id = q.move_id
            LEFT JOIN res_partner partner ON partner.id = q.partner_id
        """, base_query)

    # ---------------------------------------------------------
    # Push values into UI columns
    # ---------------------------------------------------------
    def _get_aml_line(
        self,
        report,
        parent_line_id,
        options,
        eval_dict,
        init_bal_by_col_group,
    ):

        line = super()._get_aml_line(
            report,
            parent_line_id,
            options,
            eval_dict,
            init_bal_by_col_group,
        )

        values = eval_dict.get("values", {})


        _logger.warning("1111111111111111111111111111111111111111111111", values)

        for column, col in zip(options["columns"], line["columns"]):
            label = column.get("expression_label")

            if label == "voucher_no":
                col["name"] = values.get("voucher_no")

            elif label == "voucher_type":
                col["name"] = values.get("voucher_type")

            elif label == "invoice_no":
                col["name"] = values.get("invoice_no")

            elif label == "payment_ref":
                col["name"] = values.get("payment_ref")

            elif label == "gstin":
                col["name"] = values.get("gstin")

        return line
