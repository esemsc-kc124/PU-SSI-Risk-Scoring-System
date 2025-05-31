(function(window) {
  window.extractData = function() {
    var ret = $.Deferred();

    function onError() {
      console.log('Loading error', arguments);
      ret.reject();
    }

    function onReady(smart) {
      if (smart.hasOwnProperty('patient')) {
        var patient = smart.patient;
        var pt = patient.read();

        var obv = smart.patient.api.fetchAll({ type: 'Observation' });
        var conditions = smart.patient.api.fetchAll({ type: 'Condition' });
        var procedures = smart.patient.api.fetchAll({ type: 'Procedure' });
        var encounters = smart.patient.api.fetchAll({ type: 'Encounter' });
        var medications = smart.patient.api.fetchAll({ type: 'MedicationRequest' })
          .catch(e => {
            console.warn("MedicationRequest failed, fallback to MedicationStatement", e);
            return smart.patient.api.fetchAll({ type: 'MedicationStatement' });
          })
          .catch(e2 => {
            console.error("Both MedicationRequest and MedicationStatement failed", e2);
            return []; // fallback to empty array
          });


        var careplans = smart.patient.api.fetchAll({ type: 'CarePlan' });
        var devices = smart.patient.api.fetchAll({ type: 'Device' });
        var allergies = smart.patient.api.fetchAll({ type: 'AllergyIntolerance' });

        $.when(pt, obv, conditions, procedures, encounters, medications, careplans, devices, allergies).fail(onError);

        $.when(pt, obv, conditions, procedures, encounters, medications, careplans, devices, allergies).done(function(patient, obv, conditions, procedures, encounters, medications, careplans, devices, allergies) {
          var byCodes = smart.byCodes(obv, 'code');

          var gender = patient.gender || '';
          var fname = (patient.name && patient.name[0] && patient.name[0].given) ? patient.name[0].given.join(' ') : '';
          var lname = (patient.name && patient.name[0] && patient.name[0].family) ? patient.name[0].family : '';
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

          // Debug: log full resources
          console.log("Conditions:", conditions);
          console.log("Procedures:", procedures);
          console.log("Encounters:", encounters);
          console.log("Medications:", medications);
          console.log("CarePlans:", careplans);
          console.log("Devices:", devices);
          console.log("Allergies:", allergies);

          // Append data to HTML lists
          appendToList('#condition-list', conditions.map(c => c.code?.text || 'No Description'));
          appendToList('#procedure-list', procedures.map(p => p.code?.text || 'No Description'));
          appendToList('#encounter-list', encounters.map(e => e.type?.[0]?.text || 'No Description'));
          appendToList('#medication-list', medications.map(m => m.medicationCodeableConcept?.text || 'No Description'));
          appendToList('#careplan-list', careplans.map(cp => cp.description || 'No Description'));
          appendToList('#device-list', devices.map(d => d.type?.text || 'No Description'));
          appendToList('#allergy-list', allergies.map(a => a.code?.text || 'No Description'));

          ret.resolve(p);
        });
      } else {
        onError();
      }
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
    var formattedBPObservations = [];
    BPObservations.forEach(function(observation) {
      var BP = observation.component?.find(function(component) {
        return component.code.coding?.find(function(coding) {
          return coding.code === typeOfPressure;
        });
      });
      if (BP) {
        observation.valueQuantity = BP.valueQuantity;
        formattedBPObservations.push(observation);
      }
    });
    return getQuantityValueAndUnit(formattedBPObservations[0]);
  }

  function getQuantityValueAndUnit(ob) {
    if (ob?.valueQuantity?.value !== undefined && ob?.valueQuantity?.unit !== undefined) {
      return ob.valueQuantity.value + ' ' + ob.valueQuantity.unit;
    }
    return undefined;
  }

  function appendToList(selector, items) {
    const $el = $(selector);
    if ($el.length === 0) return;
    if (items.length === 0) {
      $el.append('<li>No data available</li>');
    } else {
      items.forEach(i => $el.append(`<li>${i}</li>`));
    }
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
