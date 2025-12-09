# Copyright 2021 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    approver_id = fields.Many2one(
        "res.users",
        string="Responsible for Approval",
        compute="_compute_approver_id",
        readonly=False,
        store=True,
    )
    is_approver_id_readonly = fields.Boolean(
        compute="_compute_is_approver_id_readonly",
        help="technical field to allow complex readonly attribute "
        "logic for the approver_id field on the views",
    )

    def _compute_is_approver_id_readonly(self):
        is_account_manager = self.env.user.has_group("account.group_account_manager")
        for record in self:
            if is_account_manager and not record.review_ids:
                record.is_approver_id_readonly = False
            else:
                record.is_approver_id_readonly = True

    @api.depends("partner_id")
    def _compute_approver_id(self):
        for rec in self:
            if rec.approver_id:
                # assign a value in any case
                rec.approver_id = rec.approver_id
            elif rec.partner_id.approver_id:
                rec.approver_id = rec.partner_id.approver_id
            else:
                rec.approver_id = False

    def _post(self, soft=True):
        for move in self:
            require_approver_in_vendor_bills = (
                move.company_id.require_approver_in_vendor_bills
            )
            if (
                move.is_purchase_document(include_receipts=True)
                and require_approver_in_vendor_bills
                and not move.approver_id
            ):
                raise UserError(
                    self.env._(
                        "It is mandatory to indicate a Responsible for Approval (in {})"
                    ).format(move.name)
                )
        return super()._post(soft)
