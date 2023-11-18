odoo.define('pos_iot_six.payment', function (require) {
"use strict";

var { PaymentWorldline } = require('@pos_iot/js/payment');


var PaymentSix = PaymentWorldline.extend({
    get_payment_data: function (cid) {
        const paymentline = this.pos.get_order().get_paymentline(cid);
        const pos = this.pos;
        return {
            messageType: 'Transaction',
            transactionType: paymentline.transactionType,
            amount: Math.round(paymentline.amount*100),
            currency: pos.currency.name,
            cid: cid,
            posId: pos.pos_session.name,
            userId: pos.pos_session.user_id[0],
        };
    },

    send_payment_request: function (cid) {
        var paymentline = this.pos.get_order().get_paymentline(cid);
        paymentline.transactionType = 'Payment';

        return this._super.apply(this, arguments);
    },
});

return {
    PaymentSix: PaymentSix,
};

});
