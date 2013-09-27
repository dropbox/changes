/**
 * Inspired by the jQuery Knob project
 * https://github.com/aterrien/jQuery-Knob
 */

 var Dial = function Dial(element, options) {
    this.startAngle = null;
    this.xy = null;
    this.radius = null;
    this.lineWidth = null;
    this.scale = 1;
    this.ctx = null;
    this.v = null;
    this.$canvas = null;
    this.$element = $(element);

    this.options = $.extend({
        min: 0,
        max: 100,
        thickness: 0.35,
        lineCap: 'butt',
        width: 200,
        height: 200,
        bgColor: '#EEEEEE',
        fgColor: '#87CEEB',
    }, options || {});


    this.val = function (v) {
        if (v !== null) {
            this.v = Math.max(Math.min(v, this.options.max), this.options.min);
            this.draw();
        } else {
            return this.v;
        }
    };

    this.init = function () {
        this.$canvas = $(document.createElement('canvas'));
        if (typeof G_vmlCanvasManager !== 'undefined') {
          G_vmlCanvasManager.initElement(this.$canvas[0]);
        }
        this.ctx = this.$canvas[0].getContext ? this.$canvas[0].getContext('2d') : null;

        this.scale = (window.devicePixelRatio || 1) / (
            this.ctx.webkitBackingStorePixelRatio ||
            this.ctx.mozBackingStorePixelRatio ||
            this.ctx.msBackingStorePixelRatio ||
            this.ctx.oBackingStorePixelRatio ||
            this.ctx.backingStorePixelRatio || 1
        );

        this.width = this.options.width * this.scale;
        this.height = this.options.height * this.scale;
        this.$canvas.attr({
            width: this.width,
            height: this.height
        });

        this.$element.html(this.$canvas);

        this.xy = (this.width / 2) * this.scale;
        this.lineWidth = this.xy * this.options.thickness;
        this.lineCap = this.options.lineCap;
        this.radius = this.xy - this.lineWidth / 2;

        // deg to rad
        this.angleOffset = Math.PI / 180;
        this.angleArc = 360 * Math.PI / 180;

        // compute start and end angles
        this.startAngle = 1.5 * Math.PI + this.angleOffset;
        this.endAngle = 1.5 * Math.PI + this.angleOffset + this.angleArc;

        var s = Math.max(
            String(Math.abs(this.options.max)).length,
            String(Math.abs(this.options.min)).length,
            2
        ) + 2;

    };

    this.angle = function (v) {
        return (v - this.options.min) * this.angleArc / (this.options.max - this.options.min);
    };

    this.set = function(k, v) {
        this.options[k] = v;
        this.draw();
    }

    this.draw = function () {
        var c = this.ctx,                 // context
            a = this.angle(this.v)    // Angle
            , sat = this.startAngle     // Start angle
            , eat = sat + a             // End angle
            , sa, ea                    // Previous angles
            , r = 1;

        c.lineWidth = this.lineWidth;

        c.lineCap = this.lineCap;

        c.beginPath();
        c.strokeStyle = this.options.bgColor;
        c.arc(this.xy, this.xy, this.radius, this.endAngle, this.startAngle, true);
        c.stroke();

        c.beginPath();
        c.strokeStyle = this.options.fgColor;
        c.arc(this.xy, this.xy, this.radius, sat, eat, false);
        c.stroke();
    };

    this.init();
    this.val(this.$element.data('value') || this.options.min);
    this.draw();
};
