# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMoveReimportAttachmentWizard(models.TransientModel):

    _name = "account.move.reimport.attachment.wizard"
    _description = "Re-import Invoice from Attachment"

    move_id = fields.Many2one(
        comodel_name="account.move",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment",
        required=True,
        domain="[('id', 'in', available_attachment_ids)]",
    )
    available_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        compute="_compute_available_attachment_ids",
        string="Available Attachments",
        help="Attachments linked to the invoice.",
    )

    @api.depends("move_id")
    def _compute_available_attachment_ids(self):
        for rec in self:
            if not rec.move_id:
                rec.available_attachment_ids = False
                continue
            rec.available_attachment_ids = (
                self.env["ir.attachment"].search(
                    [
                        ("res_model", "=", rec.move_id._name),
                        ("res_id", "=", rec.move_id.id),
                    ]
                )
                + rec.move_id.message_main_attachment_id
            )

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group(
            "account_invoice_reimport_from_attachment."
            "group_invoice_reimport_from_attachment"
        ):
            raise AccessError(
                _("You are not allowed to re-import invoices from attachments.")
            )
        if self.move_id.state != "draft":
            raise UserError(_("You can only re-import lines on a draft invoice."))
        return self.move_id.action_reimport_from_attachment(self.attachment_id)
