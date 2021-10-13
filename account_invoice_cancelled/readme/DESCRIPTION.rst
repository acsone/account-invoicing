This module add a boolean in account.move : is_cancelled_by_refund
This field is set to true if the invoice is in status 'paid' and if the field refund_invoice_ids is not False 
The field refund_invoice_ids comes from this OCA module : account_invoice_refund_link

