odoo.define('pos_iot_six.models', function (require) {

var models = require('@point_of_sale/js/models');
var { PaymentSix } = require('pos_iot_six.payment');

models.register_payment_method('six_iot', PaymentSix);
});
