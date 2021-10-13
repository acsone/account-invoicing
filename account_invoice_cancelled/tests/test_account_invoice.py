# Copyright 2021 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common


class TestAccountinvoice(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_model = cls.env["account.account"]
        cls.account_invoice_obj = cls.env["account.move"]
        cls.partner_obj = cls.env["res.partner"]

        cls.journalrec = cls.env["account.journal"].create(
            {
                "name": "Journal 1",
                "code": "J1",
                "type": "sale",
                "company_id": cls.env.user.company_id.id,
            }
        )
        cls.partner3 = cls.partner_obj.create({"name": "Test partner"})

        account_user_type = cls.env.ref("account.data_account_type_receivable")

        # only adviser can create an account
        cls.account_rec1_id = cls.account_model.create(
            dict(
                code="cust_acc",
                name="customer account",
                user_type_id=account_user_type.id,
                reconcile=True,
            )
        )

        revenue_account = cls.env["account.account"].search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_revenue").id,
                )
            ],
            limit=1,
        )

        invoice_lines = [
            (
                0,
                0,
                {
                    "name": "Test description #1",
                    "product_id": cls.env.ref("product.product_product_5").id,
                    "account_id": revenue_account.id,
                    "quantity": 1.0,
                    "price_unit": 100.0,
                },
            ),
        ]

        cls.invoice = cls.account_invoice_obj.create(
            {
                "partner_id": cls.partner3.id,
                "move_type": "out_invoice",
                "invoice_line_ids": invoice_lines,
            }
        )

        cls.invoice.action_post()

        cls.register_payments_model = cls.env["account.payment.register"]
        cls.refund_model = cls.env["account.move"]
        cls.payment_method_manual_in = cls.env.ref(
            "account.account_payment_method_manual_in"
        )
        cls.journal_obj = cls.env["account.journal"]
        cls.bank_journal_euro = cls.journal_obj.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BNK67",
            }
        )
        cls.sale_journal_euro = cls.journal_obj.create(
            {
                "name": "Sale",
                "type": "sale",
                "code": "BNK67",
            }
        )

    def test_is_cancelled_by_refund_false(self):

        ctx = {
            "active_model": self.invoice._name,
            "active_ids": self.invoice.ids,
        }
        pmt_wizard = self.register_payments_model.with_context(ctx).create(
            {
                "payment_date": "2017-01-01",
                "journal_id": self.bank_journal_euro.id,
                "payment_method_id": self.payment_method_manual_in.id,
            }
        )
        pmt_wizard._create_payments()

        self.assertEqual(self.invoice.payment_state, "paid")
        self.assertFalse(self.invoice.is_cancelled_by_refund)

    def test_is_cancelled_by_refund_true(self):
        """ctx = {
            'active_model': self.invoice._name,
            'active_ids': self.invoice.ids,
        }
        wizard_obj = self.refund_model.with_context(ctx)
        refund = wizard_obj.create({
            'filter_refund': 'cancel',
            'description': 'Refund Donation invoice',
        })
        refund.invoice_refund()"""

        self.refund_reason = "The refund reason"
        self.env["account.move.reversal"].with_context(
            active_ids=self.invoice.ids,
            active_model=self.invoice._name,
        ).create(
            {"refund_method": "cancel", "reason": self.refund_reason}
        ).reverse_moves()

        self.assertEqual(self.invoice.payment_state, "reversed")
        self.assertTrue(self.invoice.is_cancelled_by_refund)
