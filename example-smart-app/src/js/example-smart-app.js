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
          var fname = (patient.name && patient.name[0]?.given) ? patient.name[0].given.join(' ') : '';
          var lname = (patient.name && patient.name[0]?.family) ? patient.name[0].family : '';
          var birthdate = patient.birthDate || '';

          var height = byCodes('8302-2');
          var systolicbp = getBloodPressureValue(byCodes('55284-4'), '8480-6');
          var diastolicbp = getBloodPressureValue(byCodes('55284-4'), '8462-4');
          var hdl = byCodes('2085-9');
          var ldl = byCodes('2089-1');

          var p = defaultPatient();
          p.birthdate = birthdate;
          p.gender = gender;
          p.fname = fname;
          p.lname = lname;
          p.height = getQuantityValueAndUnit(height[0]);
          p.systolicbp = systolicbp;
          p.diastolicbp = diastolicbp;
          p.hdl = getQuantityValueAndUnit(hdl[0]);
          p.ldl = getQuantityValueAndUnit(ldl[0]);

          appendToList('#condition-list', conditions.map(c => c.code?.text || 'No Description'));
          appendToList('#procedure-list', procedures.map(p => p.code?.text || 'No Description'));
          appendToList('#encounter-list', encounters.map(e => e.type?.[0]?.text || 'No Description'));
          appendToList('#careplan-list', careplans.map((cp, i) => cp.description || `No Description (${i + 1})`));
          appendToList('#device-list', devices.map(d => d.type?.text || 'No Description'));
          appendToList('#allergy-list', allergies.map(a => a.code?.text || 'No Description'));

          ret.resolve(p);
        });
    }

    FHIR.oauth2.ready(onReady, onError);
    return ret.promise();
  };

  function defaultPatient() {
    return {
      fname: { value: '' },
      lname: { value: '' },
      gender: { value: '' },
      birthdate: { value: '' },
      height: { value: '' },
      systolicbp: { value: '' },
      diastolicbp: { value: '' },
      ldl: { value: '' },
      hdl: { value: '' },
    };
  }

  function getBloodPressureValue(BPObservations, typeOfPressure) {
    var formatted = [];
    BPObservations.forEach(function(obs) {
      var comp = obs.component?.find(c => c.code.coding?.some(coding => coding.code === typeOfPressure));
      if (comp) {
        obs.valueQuantity = comp.valueQuantity;
        formatted.push(obs);
      }
    });
    return getQuantityValueAndUnit(formatted[0]);
  }

  function getQuantityValueAndUnit(ob) {
    if (ob?.valueQuantity?.value !== undefined && ob?.valueQuantity?.unit !== undefined) {
      return ob.valueQuantity.value + ' ' + ob.valueQuantity.unit;
    }
    return undefined;
  }

  function appendToList(selector, items) {
    const $el = $(selector);
    $el.empty();

    if (items.length === 0) {
      $el.append('<li>No data available</li>');
      return;
    }

    items.forEach(i => $el.append(`<li>${i}</li>`));
  }

  window.drawVisualization = function(p) {
    $('#holder').show();
    $('#loading').hide();
    $('#fname').html(p.fname);
    $('#lname').html(p.lname);
    $('#gender').html(p.gender);
    $('#birthdate').html(p.birthdate);
    $('#height').html(p.height);
    $('#systolicbp').html(p.systolicbp);
    $('#diastolicbp').html(p.diastolicbp);
    $('#ldl').html(p.ldl);
    $('#hdl').html(p.hdl);
  };
})(window);
