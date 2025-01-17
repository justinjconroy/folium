# -*- coding: utf-8 -*-

from folium.elements import JSCSSMixin
from folium.features import GeoJson
from folium.map import Layer

from jinja2 import Template


class TimeSliderChoropleth(JSCSSMixin, Layer):
    """
    Creates a TimeSliderChoropleth plugin to append into a map with Map.add_child.

    Parameters
    ----------
    data: str
        geojson string
    styledict: dict
        A dictionary where the keys are the geojson feature ids and the values are
        dicts of `{time: style_options_dict}`
    name : string, default None
        The name of the Layer, as it will appear in LayerControls.
    overlay : bool, default False
        Adds the layer as an optional overlay (True) or the base layer (False).
    control : bool, default True
        Whether the Layer will be included in LayerControls.
    show: bool, default True
        Whether the layer will be shown on opening (only for overlays).

    """
    _template = Template(u"""
        {% macro script(this, kwargs) %}
            var timestamps = {{ this.timestamps|tojson }};
            var styledict = {{ this.styledict|tojson }};
            var customlbl = {{ this.customlbl|tojson }};

            var current_hrblock = parseInt(JSON.parse(window.localStorage.getItem('current_slider_value')));

            var current_timestamp = timestamps[current_hrblock];
            var current_lbl = customlbl[current_hrblock];

            // insert time slider
            d3.select("body").insert("p", ":first-child").append("input")
                .attr("type", "range")
                .attr("width", "100px")
                .attr("min", 0)
                .attr("max", timestamps.length - 1)
                .attr("value", current_hrblock)
                .attr("id", "slider")
                .attr("step", "1")
                .style('align', 'center');
            
            // insert time slider output BEFORE time slider (text on top of slider)
            d3.select("body").insert("p", ":first-child").append("xhtml")
                .attr("width", "100")
                .attr("id", "slider-value")
                .style('font-size', '18px')
                .style('text-align', 'center')
                .style('font-weight', '500%');

            fill_map = function(){
                for (var feature_id in styledict){
                    let style = styledict[feature_id]//[current_timestamp];
                    var fillColor = 'white';
                    var opacity = 0;
                    if (current_timestamp in style){
                        fillColor = style[current_timestamp]['color'];
                        opacity = style[current_timestamp]['opacity'];
                        d3.selectAll('#feature-'+feature_id
                        ).attr('fill', fillColor)
                        .style('fill-opacity', opacity);
                    }
                }
            }

            d3.select("#slider").on("input", function() {
                current_timestamp = timestamps[this.value];
                current_lbl = customlbl[this.value];
                var dateslider = new Date(parseInt(current_timestamp)*1000);
                dateslider = changeTimezone(dateslider, "America/Los_Angeles");
                var datestring = "<strong>Date: </strong>" + dateslider.toLocaleDateString() + " <strong>- Time: </strong>" + dateslider.toLocaleTimeString() + " (PST)";
                d3.select("xhtml#slider-value").html("<p style='text-align:center; font-family: Garamond, serif;'>" + datestring + current_lbl + "</p>");
                window.localStorage.setItem('current_slider_value', this.value);
                fill_map();
            });

            {% if this.highlight %}
                {{this.get_name()}}_onEachFeature = function onEachFeature(feature, layer) {
                    layer.on({
                        mouseout: function(e) {
                        if (current_timestamp in styledict[e.target.feature.id]){
                            var opacity = styledict[e.target.feature.id][current_timestamp]['opacity'];
                            d3.selectAll('#feature-'+e.target.feature.id).style('fill-opacity', opacity);
                        }
                    },
                        mouseover: function(e) {
                        if (current_timestamp in styledict[e.target.feature.id]){
                            d3.selectAll('#feature-'+e.target.feature.id).style('fill-opacity', 1);
                        }
                    },
                        click: function(e) {
                            {{this._parent.get_name()}}.fitBounds(e.target.getBounds());
                    }
                    });
                };
            {% endif %}

            var {{ this.get_name() }} = L.geoJson(
                    {{ this.data|tojson }}
            ).addTo({{ this._parent.get_name() }});

            {{ this.get_name() }}.setStyle(function(feature) {
                if (feature.properties.style !== undefined){
                    return feature.properties.style;
                }
                else{
                    return "";
                }
            });

         function changeTimezone(date, ianatz) {

              // suppose the date is 12:00 UTC
              var invdate = new Date(date.toLocaleString('en-US', {
                timeZone: ianatz
              }));

              // then invdate will be 07:00 in Toronto
              // and the diff is 5 hours
              var diff = date.getTime() - invdate.getTime();

              // so 12:00 in Toronto is 17:00 UTC
              return new Date(date.getTime() - diff); // needs to substract

            }

	    function onOverlayAdd(e) {
                {{ this.get_name() }}.eachLayer(function (layer) {
                    layer._path.id = 'feature-' + layer.feature.id;
                });

                d3.selectAll('path')
                .attr('stroke', 'white')
                .attr('stroke-width', 0.8)
                .attr('stroke-dasharray', '5,5')
                .attr('fill-opacity', 0);

                fill_map();
            }

            {{ this._parent.get_name() }}.on('overlayadd', onOverlayAdd);


            onOverlayAdd(); // fill map as layer is loaded
            
            var dateslider = new Date(parseInt(current_timestamp)*1000);
            dateslider = changeTimezone(dateslider, "America/Los_Angeles");
            var datestring = "<strong>Date: </strong>" + dateslider.toLocaleDateString() + " <strong>- Time: </strong>" + dateslider.toLocaleTimeString() + " (PST)";
            d3.select("xhtml#slider-value").html("<p style='text-align:center; font-family: Garamond, serif;'>" + datestring + current_lbl + "</p>");

        {% endmacro %}
        """)

    default_js = [
        ('d3v4',
         'https://d3js.org/d3.v4.min.js')
    ]

    def __init__(self, data, styledict, customlbl=[], name=None, overlay=True, control=True,
                 show=True):
        super(TimeSliderChoropleth, self).__init__(name=name, overlay=overlay,
                                                   control=control, show=show)
        self.data = GeoJson.process_data(GeoJson({}), data)

        if not isinstance(styledict, dict):
            raise ValueError('styledict must be a dictionary, got {!r}'.format(styledict))  # noqa
        for val in styledict.values():
            if not isinstance(val, dict):
                raise ValueError('Each item in styledict must be a dictionary, got {!r}'.format(val))  # noqa

        # Make set of timestamps.
        timestamps = set()
        for feature in styledict.values():
            timestamps.update(set(feature.keys()))
        timestamps = sorted(list(timestamps))

        self.timestamps = timestamps
        self.styledict = styledict
        if len(customlbl) == 0: 
            raise ValueError('Oops!')
            customlbl = ["" for x in range(len(timestamps))] #create empty string array if no custom label supplied
        elif len(timestamps) != len(customlbl):
            raise ValueError('Number of elements in customlbl must equal number of time stamps')
        self.customlbl = customlbl
        
