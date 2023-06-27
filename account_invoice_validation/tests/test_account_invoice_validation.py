# Copyright 2023 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import timedelta
from uuid import uuid4

from odoo import exceptions, fields
from odoo.fields import first
from odoo.tests.common import TransactionCase


class TestAccountMove(TransactionCase):
    """
    Tests for account.invoice
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def setUp(self):
        super().setUp()
        self.invoice_obj = self.env["account.move"]
        self.account_obj = self.env["account.account"]
        self.product_obj = self.env["product.product"]
        self.users_obj = self.env["res.users"]
        self.supplier = self.env.ref("base.res_partner_3")
        self.supplier2 = self.env.ref("base.res_partner_4")
        self.account_manager_group = self.env.ref("account.group_account_user")
        self.invoice_group = self.env.ref("account.group_account_invoice")
        today = fields.Date.from_string(fields.Date.today())
        tomorrow = today + timedelta(hours=24)
        yesterday = today - timedelta(hours=24)
        self.pending_date_yesterday = fields.Date.to_string(yesterday)
        self.pending_date_today = fields.Date.to_string(today)
        self.pending_date_tomorrow = fields.Date.to_string(tomorrow)
        self._prepare_test()

    def _prepare_test(self):
        """
        Prepare some data for tests cases.
        - Create 2 users: 1 for supplier
        - A supplier (with validation_user_id filled)
        - Create a supplier invoice
        - Create a supplier refund
        - Create a customer invoice
        :return: bool
        """
        users_obj = self.users_obj
        invoice_obj = self.invoice_obj
        account_obj = self.account_obj
        supplier = self.supplier
        company = self.env.company
        account_manager_group = self.account_manager_group
        account_payable = self.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        account_receivable = self.env["account.account"].search(
            [("account_type", "=", "asset_receivable"), ("company_id", "=", company.id)]
        )
        self.account_payable = account_payable = account_obj.create(
            {
                "code": "220000bis",
                "name": "Expenses unit test",
                "reconcile": True,
            }
        )
        self.account_receivable = account_receivable = account_obj.create(
            {
                "code": "200000bis",
                "name": "Sale unit test",
                "reconcile": True,
            }
        )
        # Check if the supplier is really a supplier
        self.assertTrue(supplier.supplier_rank >= 0)
        self.user1 = users_obj.create(
            {
                "name": "Unit test User 1",
                "login": "account_invoice_validation1",
                "email": "test1@acsone.eu",
                "groups_id": [(6, 0, account_manager_group.ids)],
            }
        )
        self.user2 = users_obj.create(
            {
                "name": "Unit test User 2",
                "login": "account_invoice_validation2",
                "email": "test2@acsone.eu",
                "groups_id": [(6, 0, account_manager_group.ids)],
            }
        )

        supplier_invoice_values = {
            "partner_id": supplier.id,
            "move_type": "in_invoice",
            "validation_state": "wait_approval",
            "invoice_line_ids": [
                (
                    0,
                    False,
                    {
                        "name": "Line 1",
                        "account_id": account_payable.id,
                        "quantity": 1,
                        "price_unit": 250.25,
                    },
                ),
            ],
        }
        self.supplier_invoice = invoice_obj.create(supplier_invoice_values)
        supplier_refund_values = {
            "move_type": "in_refund",
            "validation_state": "wait_approval",
            "partner_id": supplier.id,
            "invoice_line_ids": [
                (
                    0,
                    False,
                    {
                        "name": "Line 2 refunded",
                        "account_id": account_payable.id,
                        "quantity": 3,
                        "price_unit": 300.68,
                    },
                ),
            ],
        }
        customer_invoice_values = {
            "partner_id": supplier.id,
            "move_type": "out_invoice",
            "invoice_line_ids": [
                (
                    0,
                    False,
                    {
                        "name": "Line 1",
                        "account_id": account_receivable.id,
                        "quantity": 2,
                        "price_unit": 523.36,
                    },
                ),
            ],
        }
        self.supplier_refund = invoice_obj.create(supplier_refund_values)
        self.customer_invoice = invoice_obj.create(customer_invoice_values)
        return True
    
    def test_update_validation_state1(self):
        """
        Test some validation_state function.
        These function must update the validation_state for
        supplier invoice/refund only.
        In this case, we only call some function related to this update
        (on a supplier refund).
        No error should be raised.
        :return: bool
        """
        supplier_refund = self.supplier_refund
        pending_date = self.pending_date_tomorrow
        message = "Message test"
        reference = str(uuid4())
        today = fields.Date.today()
        supplier_refund.validation_state_wait_approval()
        self.assertEqual(supplier_refund.validation_state, "wait_approval")
        supplier_refund.validation_state_accepted(
            supplier_refund.partner_id.id, reference, today
        )
        self.assertEqual(supplier_refund.validation_state, "accepted")
        supplier_refund.action_block_state_continue(message, pending_date)
        self.assertEqual(supplier_refund.validation_state, "locked")
        supplier_refund.action_refuse_state_continue("I refuse")
        self.assertEqual(supplier_refund.validation_state, "refused")
        return True

    def test_update_validation_state2(self):
        """
        Test some validation_state function.
        These function must update the validation_state for
        supplier invoice/refund only.
        In this case, we only call some function related to this update
        (on a supplier invoice).
        No error should be raised.
        :return: bool
        """
        supplier_invoice = self.supplier_invoice
        pending_date = self.pending_date_tomorrow
        message = "Test message unit test"
        supplier_invoice.validation_state_wait_approval()
        reference = str(uuid4())
        today = fields.Date.today()
        self.assertEqual(supplier_invoice.validation_state, "wait_approval")
        supplier_invoice.validation_state_accepted(
            supplier_invoice.partner_id.id, reference, today
        )
        self.assertEqual(supplier_invoice.validation_state, "accepted")
        supplier_invoice.action_block_state_continue(message, pending_date)
        self.assertEqual(supplier_invoice.validation_state, "locked")
        supplier_invoice.action_refuse_state_continue("I refuse")
        self.assertEqual(supplier_invoice.validation_state, "refused")
        return True

    def test_update_validation_state3(self):
        """
        Test some validation_state function.
        These function must update the validation_state for
        supplier invoice/refund only.
        In this case, we're trying to apply/update these state on a normal
        customer invoice.
        Exception should be raised
        Test must be done on a different invoice because the cursor can be
        locked
        :return: bool
        """
        customer_invoice1 = self.customer_invoice
        pending_date = self.pending_date_tomorrow
        customer_invoice2 = customer_invoice1.copy()
        customer_invoice3 = customer_invoice1.copy()
        customer_invoice4 = customer_invoice1.copy()
        reference = str(uuid4())
        today = fields.Date.today()
        with self.assertRaises(exceptions.ValidationError):
            customer_invoice1.validation_state_wait_approval()
        with self.assertRaises(exceptions.ValidationError):
            customer_invoice2.validation_state_accepted(
                customer_invoice2.partner_id.id, reference, today
            )
        with self.assertRaises(exceptions.ValidationError):
            customer_invoice3.action_block_state_continue("Test", pending_date)
        with self.assertRaises(exceptions.ValidationError):
            customer_invoice4.action_refuse_state_continue("I don't know")
        return True

    def test_redirect_approval1(self):
        """
        Test the redirect_approval function.
        Using a user id, update current supplier
        invoice/refund with these given parameter.
        For this test, apply the function on a valid recordset. So no error
        should be raised.
        We also check if the new validation user is correctly added into
        followers
        :return: bool
        """
        invoices = self.supplier_refund
        invoices |= self.supplier_invoice
        user = self.env.user
        note = str(uuid4())
        today = fields.Date.today()
        nb_message = len(invoices.mapped("message_ids"))
        invoices.write(
            {
                "validation_user_id": user,
                "partner_id": self.supplier2,
            }
        )
        invoices.action_assign_continue(note)
        for invoice in invoices:

            self.assertEqual(invoice.validation_user_id, user)
            self.assertEqual(invoice.date_assignation, today)
            self.assertEqual(invoice.partner_id, self.supplier2)
            bodies = invoice.message_ids.mapped("body")
            is_inside = any(note in bdy for bdy in bodies)
            self.assertTrue(is_inside)
            partners = invoice.message_follower_ids.mapped("partner_id")
            self.assertIn(user.partner_id.id, partners.ids)
        # We add the number of invoices because we have at least 1 message
        # (the note) per invoice
        nb_message_after = nb_message + len(invoices)
        self.assertGreaterEqual(nb_message_after, nb_message)
        return True

    def test_validation_state_locked1(self):
        """
        Test the validation_state_locked function.
        This function should lock the purchase invoice/refund (by the
        validation_state). And also fill the pending_date (with constraint).
        For this test, we put an invalid pending date (yesterday)
        :return: bool
        """
        invoice = self.supplier_refund
        pending_date = self.pending_date_yesterday
        with self.assertRaises(exceptions.UserError):
            invoice.action_block_state_continue("Other message", pending_date)
        return True

    def test_validation_state_locked2(self):
        """
        Test the validation_state_locked function.
        This function should lock the purchase invoice/refund (by the
        validation_state). And also fill the pending_date (with constraint).
        For this test, we put an invalid pending date (today)
        :return: bool
        """
        invoice = self.supplier_refund
        pending_date = self.pending_date_today
        with self.assertRaises(exceptions.UserError):
            invoice.action_block_state_continue("Other message", pending_date)
        return True

    def test_validation_state_locked3(self):
        """
        Test the validation_state_locked function.
        This function should lock the purchase invoice/refund (by the
        validation_state). And also fill the pending_date (with constraint).
        For this test, we put a valid pending date (tomorrow)
        :return: bool
        """
        invoice = self.supplier_refund
        pending_date = self.pending_date_tomorrow
        invoice.action_block_state_continue("Other message", pending_date)
        self.assertEqual(fields.Date.to_string(invoice.pending_date), pending_date)
        return True

    def test_validation_state_locked4(self):
        """
        Test the validation_state_locked function.
        This function should lock the purchase invoice/refund (by the
        validation_state). And also fill the pending_date (with constraint).
        For this test, we put an empty message/note so it should raise
        an exception
        :return: bool
        """
        invoice = self.supplier_refund
        pending_date = self.pending_date_tomorrow
        with self.assertRaises(exceptions.UserError):
            invoice.action_block_state_continue("", pending_date)
        return True

    def test_action_post1(self):
        """
        Test the action_post function.
        For supplier invoice/refund, we have to check the validation_state
        before validate the invoice/refund.
        The validation state must be 'accepted' to validate the invoice/refund.
        For other invoices types, we let the standard behaviour.
        In this case, we're trying to validate an 'accepted' supplier refund
        and no error should be raised.
        :return: bool
        """
        supplier_refund = self.supplier_refund
        reference = str(uuid4())
        today = fields.Date.today()
        # The refund should not be already 'posted'
        self.assertNotEqual(supplier_refund.state, "posted")
        # Set it to 'accepted'
        supplier_refund.validation_state_accepted(
            supplier_refund.partner_id.id, reference, today
        )
        self.assertEqual(supplier_refund.ref, reference)
        self.assertEqual(supplier_refund.invoice_date, today)
        supplier_refund.action_post()
        states = ["posted"]
        self.assertIn(supplier_refund.state, states)
        return True

    def test_action_post5(self):
        """
        Test the action_post function.
        For supplier invoice/refund, we have to check the validation_state
        before validate the invoice/refund.
        The validation state must be 'accepted' to validate the invoice/refund.
        For other invoices types, we let the standard behaviour.
        In this case, we're trying to validate a normal customer invoice
        and no error should be raised.
        :return: bool
        """
        customer_invoice = self.customer_invoice
        # The refund should not be already 'posted'
        self.assertNotEqual(customer_invoice.state, "posted")
        self.assertNotEqual(customer_invoice.validation_state, "accepted")
        customer_invoice.action_post()
        # We don't have to test if the state is correctly updated because
        # it's the normal behaviour and if something is not updated, we don't
        # care. We just check that no exception has been raised.
        return True

    def test_action_post7(self):
        """
        Test the action_post function.
        For supplier invoice/refund, we have to check the validation_state
        before validate the invoice/refund.
        The validation state must be 'accepted' to validate the invoice/refund.
        For other invoices types, we let the standard behaviour.
        Also, an accountant (group) can validate an purchase invoice/refund
        if the validation state is 'refused'.
        It's what we test in this case (for a purchase refund)
        :return: bool
        """
        account_manager_group = self.account_manager_group
        # Add the user to authorized accoutant group to validate
        # refused invoice
        self.env.user.write({"groups_id": [(4, account_manager_group.id, False)]})
        supplier_refund = self.supplier_refund
        supplier_refund.update(
            {
                "invoice_date": fields.Date.today(),
            }
        )
        # The refund should not be already 'posted'
        self.assertNotEqual(supplier_refund.state, "posted")
        self.assertNotEqual(supplier_refund.validation_state, "accepted")
        self.assertNotEqual(supplier_refund.validation_state, "refused")
        supplier_refund.action_refuse_state_continue("I just want to refuse it")
        self.assertEqual(supplier_refund.validation_state, "refused")
        supplier_refund.action_post()
        states = ["posted"]
        self.assertIn(supplier_refund.state, states)
        self.assertEqual(supplier_refund.validation_state, "refused")
        return True

    def test_action_post8(self):
        """
        Test the action_post function.
        For supplier invoice/refund, we have to check the validation_state
        before validate the invoice/refund.
        The validation state must be 'accepted' to validate the invoice/refund.
        For other invoices types, we let the standard behaviour.
        Also, an accountant (group) can validate an purchase invoice/refund
        if the validation state is 'refused'.
        It's what we test in this case (for a purchase invoice)
        :return: bool
        """
        supplier_invoice = self.supplier_invoice
        supplier_invoice.update(
            {
                "invoice_date": fields.Date.today(),
            }
        )
        account_manager_group = self.account_manager_group
        # Add the user to authorized accoutant group to validate
        # refused invoice
        self.env.user.write({"groups_id": [(4, account_manager_group.id, False)]})
        # The refund should not be already 'posted'
        self.assertNotEqual(supplier_invoice.state, "posted")
        self.assertNotEqual(supplier_invoice.validation_state, "accepted")
        self.assertNotEqual(supplier_invoice.validation_state, "refused")
        supplier_invoice.action_refuse_state_continue("I want to refuse again")
        self.assertEqual(supplier_invoice.validation_state, "refused")
        supplier_invoice.action_post()
        states = ["posted"]
        self.assertIn(supplier_invoice.state, states)
        self.assertEqual(supplier_invoice.validation_state, "refused")
        return True

    def test_validation_state_refused1(self):
        """
        Test the validation_state_refused function.
        This function should update the state to refused (already check by
        another test) and also put the message into message_ids.
        In this case, we just ensure that the message is created
        :return: bool
        """
        invoices = self.supplier_refund
        invoices |= self.supplier_invoice
        note = str(uuid4())
        nb_message = len(invoices.mapped("message_ids"))
        invoices.action_refuse_state_continue(note)
        # We add the number of invoices because we have at least 1 message
        # (the note) per invoice
        nb_message_after = nb_message + len(invoices)
        self.assertGreaterEqual(nb_message_after, nb_message)
        for invoice in invoices:
            bodies = invoice.message_ids.mapped("body")
            is_inside = any(note in bdy for bdy in bodies)
            self.assertTrue(is_inside)
        return True

    def test_compute_account_move_line(self):
        """
        Test to change partner on account_move that changes account_id
        """
        # creat invoice to have previous data on supplier 2
        supplier_invoice_values = {
            "partner_id": self.supplier2.id,
            "move_type": "in_invoice",
            "validation_state": "wait_approval",
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                (
                    0,
                    False,
                    {
                        "name": "Line 1",
                        "quantity": 1,
                        "price_unit": 250.25,
                    },
                ),
            ],
        }
        self.invoice_obj.create(supplier_invoice_values)._post()

        # Invoice line without any product
        supplier_invoice_values = {
            "partner_id": self.supplier.id,
            "move_type": "in_invoice",
            "validation_state": "wait_approval",
            "invoice_line_ids": [
                (
                    0,
                    False,
                    {
                        "account_id": self.account_payable.id,
                        "name": "Line 1",
                        "quantity": 1,
                        "price_unit": 250.25,
                    },
                ),
            ],
        }
        supplier_invoice = self.invoice_obj.create(supplier_invoice_values)
        invoice_line_id = supplier_invoice.invoice_line_ids
        account_id = invoice_line_id.account_id

        self.assertEqual(len(invoice_line_id), 1)
        self.assertEqual(account_id.id, self.account_payable.id)

        most_used_account_supplier2 = self.env[
            "account.account"
        ]._get_most_frequent_account_for_partner(
            company_id=invoice_line_id.company_id.id,
            partner_id=self.supplier2.id,
            move_type=invoice_line_id.move_id.move_type,
        )

        supplier_invoice.write({"partner_id": self.supplier2.id})

        # Will change account to most used account of supplier2
        invoice_line_id = supplier_invoice.invoice_line_ids
        new_account_id = invoice_line_id.account_id
        self.assertEqual(new_account_id.id, most_used_account_supplier2)
        self.assertNotEqual(new_account_id.id, account_id.id)

        # The default behaviour of Odoo would be to remove account
        # on account move lines because
        # new partner hasn't any "most_frequent account"
        # but now, we will keep the old account_id

        partner_a = self.env["res.partner"].create(
            {
                "name": "partner_a",
            }
        )

        most_used_account_partnera = self.env[
            "account.account"
        ]._get_most_frequent_account_for_partner(
            company_id=invoice_line_id.company_id.id,
            partner_id=partner_a.id,
            move_type=invoice_line_id.move_id.move_type,
        )

        # remove default account on journal id
        supplier_invoice.journal_id.default_account_id = False

        supplier_invoice.write({"partner_id": partner_a.id})

        old_account_id = new_account_id
        invoice_line_id = supplier_invoice.invoice_line_ids
        new_account_id = invoice_line_id.account_id

        self.assertFalse(most_used_account_partnera)
        # the account stays the same
        self.assertEqual(old_account_id, new_account_id)
