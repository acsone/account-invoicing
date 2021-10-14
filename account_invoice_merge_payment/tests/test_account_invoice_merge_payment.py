# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountInvoiceMergePayment(TransactionCase):
    """
    Tests for Account Invoice Merge.
    """

    def setUp(self):
        super().setUp()
        self.par_model = self.env["res.partner"]
        self.context = self.env["res.users"].context_get()
        self.acc_model = self.env["account.account"]
        self.inv_model = self.env["account.move"]
        self.inv_line_model = self.env["account.move.line"]
        self.wiz = self.env["invoice.merge"]
        self.product = self.env.ref("product.product_product_8")
        self.account_receive = self.env.ref("account.data_account_type_receivable")
        self.partner1 = self._create_partner()
        self.partner2 = self._create_partner()
        self.invoice_account = self.acc_model.search(
            [("user_type_id", "=", self.account_receive.id)],
            limit=1,
        )
        self.journal = self.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )

        self.default_payment_mode = self.env.ref(
            "account_payment_mode.payment_mode_inbound_dd1"
        )
        self.payment_mode2 = self.env.ref(
            "account_payment_mode.payment_mode_outbound_dd2"
        )

        self.invoice1 = self._create_invoice(self.partner1, "A")
        self.invoice2 = self._create_invoice(self.partner1, "B")
        self.invoice3 = self._create_invoice(self.partner2, "C")
        self.invoice4 = self._create_invoice(self.partner2, "D")

        self.invoice_line1 = self._create_inv_line(self.invoice1)
        self.invoice_line2 = self._create_inv_line(self.invoice2)
        self.invoice_line3 = self._create_inv_line(self.invoice3)
        self.invoice_line4 = self._create_inv_line(self.invoice4)

    def _create_partner(self):
        partner = self.par_model.create(
            {"name": "Test Partner", "supplier_rank": 1, "company_type": "company"}
        )
        return partner

    def _create_inv_line(self, invoice):
        lines = invoice.invoice_line_ids
        invoice.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        False,
                        {
                            "name": "test invoice line",
                            "quantity": 1.0,
                            "price_unit": 3.0,
                            "move_id": invoice.id,
                            "product_id": self.product.id,
                            "exclude_from_invoice_tab": False,
                        },
                    )
                ]
            }
        )
        return invoice.invoice_line_ids - lines

    def _create_invoice(self, partner, name, journal=False):
        if not journal:
            journal = self.journal
        invoice = self.inv_model.create(
            {
                "partner_id": partner.id,
                "name": name,
                "move_type": "out_invoice",
                "journal_id": journal.id,
            }
        )
        return invoice

    def test_account_invoice_merge_1(self):
        self.assertEqual(len(self.invoice1.invoice_line_ids), 1)
        self.assertEqual(len(self.invoice2.invoice_line_ids), 1)
        start_inv = self.inv_model.search(
            [("state", "=", "draft"), ("partner_id", "=", self.partner1.id)]
        )
        self.assertEqual(len(start_inv), 2)
        invoices = self.invoice1 | self.invoice2
        wiz_id = self.wiz.with_context(
            active_ids=invoices.ids,
            active_model=invoices._name,
        ).create({})
        wiz_id.fields_view_get()
        action = wiz_id.merge_invoices()

        self.assertEqual(
            action["type"],
            "ir.actions.act_window",
            "There was an error and the two invoices were not merged.",
        )
        self.assertEqual(
            action["xml_id"],
            "account.action_move_out_invoice_type",
            "There was an error and the two invoices were not merged.",
        )

        end_inv = self.inv_model.search(
            [("state", "=", "draft"), ("partner_id", "=", self.partner1.id)]
        )
        self.assertEqual(len(end_inv), 1)
        self.assertEqual(len(end_inv[0].invoice_line_ids), 1)
        self.assertEqual(end_inv[0].invoice_line_ids[0].quantity, 2.0)
        self.assertEqual(end_inv.payment_mode_id, self.invoice1.payment_mode_id)

    def test_account_invoice_merge_2(self):
        self.invoice4.write({"payment_mode_id": self.payment_mode2})
        invoices = self.invoice3 | self.invoice4
        self.assertNotEqual(
            self.invoice3.payment_mode_id, self.invoice4.payment_mode_id
        )
        wiz_id = self.wiz.with_context(
            active_ids=invoices.ids,
            active_model=invoices._name,
        ).create({})
        with self.assertRaises(UserError):
            wiz_id.fields_view_get()
