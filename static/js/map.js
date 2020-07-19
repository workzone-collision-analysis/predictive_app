// mapbox accessToken
mapboxgl.accessToken = 'pk.eyJ1IjoiYWV0aGUiLCJhIjoiY2tjZjc1Y3A0MGU5MTJ0cjBkY2N5bmVwbCJ9.WUCl0i-oGT8QCSPBnpBoZg';
const script = document.currentScript;
const fullUrl = script.src;
let map;
let popup;

const popupTemplate511 =
    '<div class="map__popup">\n' +
    '<h4>511 Event information</h4>\n'+
    '<p>Crash Probability (within 900ft, %): <span id="511-info__Crash"></span></p>\n' +
    '<p>Created Time: <span id="511-info__CreateTime"></span></p>\n' +
    '<p>Closed Time: <span id="511-info__CloseTime"></span></p>\n' +
    '<p>Duration (hour): <span id="511-info__Duration"></span></p>\n' +
    '<p>Peak-time duration (hour): <span id="511-info__PeakDuration"></span></p>\n' +
    '<p>Roadway Type: <span id="511-info__Roadway"></span></p>\n' +
    '<p>Posted Speed: <span id="511-info__Speed"></span></p>\n' +
    '<p>Street Width: <span id="511-info__Width"></span></p>\n'+
    '</div>';

//import map
Promise.all([
    d3.csv(fullUrl.replace('js/map.js','data/shared_street_with_attribute.csv'))
]).then(([segmentAttribute])=>{
    map = new mapboxgl.Map({
        container: 'map__map', // container id
        style: 'mapbox://styles/aethe/ckcfhxktj05k61itg540hrgr8',
        zoom: 15,
        center: [-73.997482, 40.730880]
    });

    // set the URL of the datasets
    const shortSegmentURL = fullUrl.replace('js/map.js','data/short_segment.geojson');
    const segmentURL = fullUrl.replace('js/map.js','data/segment.geojson');

    map.on('load', function () {
        window.setInterval(function () {
            map.getSource('shortSegment').setData(shortSegmentURL);
            map.getSource('segment').setData(segmentURL);
        }, 2000);

        map.addSource('segment', {type: 'geojson', data: segmentURL, 'promoteId': 'id'});
        map.addSource('shortSegment', {type: 'geojson', data: shortSegmentURL, 'promoteId': 'id'});

        map.addLayer({
            'id': 'segment',
            'source': 'segment',
            'type': 'line',
            'paint': {
                'line-color': '#636363'
            }
        });

        map.addLayer({
            'id': 'segment_transparent',
            'source': 'segment',
            'type': 'line',
            'paint': {
                'line-color': 'rgba(0,0,0,0)',
                'line-width':6
            }
        });

        map.addLayer({
            'id': 'shortSegment',
            'source': 'shortSegment',
            'type': 'line',
            'paint': {
                'line-color': '#636363',
                'line-width': 1
            }
        });

        map.addLayer({
            'id': 'shortSegment_transparent',
            'source': 'shortSegment',
            'type': 'line',
            'paint': {
                'line-color': 'rgba(0,0,0,0)',
                'line-width':6
            }
        });
        let coords;
        map.on('click', 'segment_transparent', function (e) {
            coords = e.features[0].geometry.coordinates;
            let clicked_feature = e.features[0];
            const target = segmentAttribute.filter(d=>d.id === clicked_feature.id)[0];
            if(target !== undefined){
                document.getElementById('input-shst_id').innerText = clicked_feature.id;
                document.getElementById('input-roadway-type').value = ((target['roadway_type']!=='-1.0')&&target['roadway_type']!=='Unknown')?target['roadway_type']:'-';
                document.getElementById('input-street-width').value = ((target['posted_speed']!=='-1')&&(target['posted_speed']!=='-1.0'))?target['posted_speed']:'-';
                document.getElementById('input-posted-speed').value =  ((target['street_width']!=='-1')&&(target['street_width']!=='-1.0'))?target['street_width']:'-';
            } else {
                alert("data is missing, plz fill the form");
            }

        });

        $("#submit_button").click(function(){
            console.log(document.getElementById('input-create-time').value);
            const data = {id: document.getElementById('input-shst_id').innerText,
                          coords: coords,
                          roadway_type: document.getElementById('input-roadway-type').value,
                          street_width:  document.getElementById('input-street-width').value,
                          posted_speed: document.getElementById('input-posted-speed').value,
                          create_date: document.getElementById('input-create-date').value,
                          create_time: document.getElementById('input-create-time').value,
                          close_date: document.getElementById('input-close-date').value,
                          close_time: document.getElementById('input-close-time').value };
            console.log(data);
            $.ajax({
                type:'POST',
                contentType:'application/json',
                url:'/results',
                dataType:'json',
                data: JSON.stringify(data),
                success : function(result){
                    console.log(result);
                    console.log(result.features[0].geometry);
                    map.addSource(data['id'],{
                        'type': 'geojson',
                        'data': {
                            'type': 'Feature',
                            'geometry': result.features[0].geometry}
                    });
                    const target = result.features[0]['properties'];
                    let opacity;
                    if((target['cluster']==0)||(target['cluster']==4)){
                        opacity=0.8;
                    } else{
                        opacity=0.6;
                    }
                    map.addLayer({
                        'id': data['id'],
                        'source': data['id'],
                        'type': 'fill',
                        'paint': {
                            'fill-color': '#F44336',
                            'fill-opacity':opacity,
                            'fill-outline-color': '#F44336'
                        }
                    });
                    map.on('click', data['id'], function(e){
                        let clicked_feature = e.features[0];
                        const lngArray = clicked_feature.geometry.coordinates[0].map(d=>d[0]);
                        const latArray = clicked_feature.geometry.coordinates[0].map(d=>d[1]);
                        const lngAverage = lngArray.reduce((a, b) => a + b) / lngArray.length;
                        const latAverage = latArray.reduce((a, b) => a + b) / latArray.length;
                        if(popup!==undefined){
                            popup.remove();
                        }
                        popup = new mapboxgl.Popup()
                            .setLngLat([lngAverage,latAverage])
                            .setHTML(popupTemplate511)
                            .addTo(map);
                        document.getElementById('511-info__Crash').innerText = target['crash_rate'];
                        document.getElementById('511-info__CreateTime').innerText = target['create_time'];
                        document.getElementById('511-info__CloseTime').innerText = target['close_time'];
                        document.getElementById('511-info__Duration').innerText = Math.round(target['duration']*100)/100
                        document.getElementById('511-info__PeakDuration').innerText = Math.round(target['peak_duration']*100)/100
                        document.getElementById('511-info__Roadway').innerText = data['roadway_type'];
                        document.getElementById('511-info__Speed').innerText = data['posted_speed'];
                        document.getElementById('511-info__Width').innerText = data['street_width'];

                    });


                },
                error : function(result){
                    alert('Please check the inputs again')
                }
            })
        });
    });
});
