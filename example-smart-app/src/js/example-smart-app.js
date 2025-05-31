(function(window) {
  window.extractData = function() {
    var ret = $.Deferred();

    function onError() {
      console.log('Loading error', arguments);
      ret.reject();
    }

    function onReady(smart) {
      if (!smart.hasOwnProperty('patient')) return onError();

      var patient = smart.patient;
      var pt = patient.read();

      function safeFetch(resourceType) {
        var deferred = $.Deferred();
        smart.patient.api.fetchAll({ type: resourceType })
          .done(data => deferred.resolve(data))
          .fail(error => {
            console.warn(`${resourceType} fetch failed`, error);
            deferred.resolve([]);
          });
        return deferred.promise();
      }

      var obv = safeFetch('Observation');
      var conditions = safeFetch('Condition');
      var procedures = safeFetch('Procedure');
      var encounters = safeFetch('Encounter');
      var careplans = safeFetch('CarePlan');
      var devices = safeFetch('Device');
      var allergies = safeFetch('AllergyIntolerance');

      $.when(pt, obv, conditions, procedures, encounters, careplans, devices, allergies)
        .fail(onError)
        .done(function(patient, obv, conditions, procedures, encounters, careplans, devices, allergies) {
          var byCodes = smart.byCodes(obv, 'code');

          var gender = patient.gender || '';
          var fname = patient.name?.[0]?.given?.join(' ') || '';
          var lname = patient.name?.[0]?.family || '';
          var birthdate = patient.birthDate || '';

          var height = byCodes('8302-2');
          var systolicbp = getBloodPressureValue(byCodes('55284-4'), '8480-6');
          var diastolicbp = getBloodPressureValue(byCodes('55284-4'), '8462-4');
          var hdl = byCodes('2085-9');
          var ldl = byCodes('2089-1');

          var p = {
            fname, lname, gender, birthdate,
            height: getQuantityValueAndUnit(height[0]),
            systolicbp, diastolicbp,
            hdl: getQuantityValueAndUnit(hdl[0]),
            ldl: getQuantityValueAndUnit(ldl[0])
          };

          appendToList('#condition-list', conditions.map(c => c.code?.text || 'No Description'));
          appendToList('#procedure-list', procedures.map(p => p.code?.text || 'No Description'));
          appendToList('#encounter-list', encounters.map(e => e.type?.[0]?.text || 'No Description'));
          appendToList('#careplan-list', careplans.map(cp => cp.description || 'No Description'));
          appendToList('#device-list', devices.map(d => d.type?.text || 'No Description'));
          appendToList('#allergy-list', allergies.map(a => a.code?.text || 'No Description'));

          ret.resolve(p);
        });
    }

    FHIR.oauth2.ready(onReady, onError);
    return ret.promise();
  };

  function getBloodPressureValue(obsArray, code) {
    let valObs = obsArray.find(o => o.component?.some(c => c.code?.coding?.some(cc => cc.code === code)));
    let comp = valObs?.component?.find(c => c.code?.coding?.some(cc => cc.code === code));
    return getQuantityValueAndUnit(comp);
  }

  function getQuantityValueAndUnit(ob) {
    return (ob?.valueQuantity?.value !== undefined && ob?.valueQuantity?.unit !== undefined)
      ? ob.valueQuantity.value + ' ' + ob.valueQuantity.unit
      : undefined;
  }

  function appendToList(selector, items) {
    const $el = $(selector);
    $el.empty();
    if (items.length === 0) {
      $el.append('<li>No data available</li>');
    } else {
      items.forEach(i => $el.append(`<li>${i}</li>`));
    }
  }

  window.drawVisualization = function(p) {
    $('#holder').show();
    $('#loading').hide();
    $('#fname').text(p.fname);
    $('#lname').text(p.lname);
    $('#gender').text(p.gender);
    $('#birthdate').text(p.birthdate);
    $('#height').text(p.height);
    $('#systolicbp').text(p.systolicbp);
    $('#diastolicbp').text(p.diastolicbp);
    $('#ldl').text(p.ldl);
    $('#hdl').text(p.hdl);
  };
})(window);
