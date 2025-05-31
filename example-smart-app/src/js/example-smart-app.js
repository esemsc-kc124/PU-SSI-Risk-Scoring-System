(function(window){
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
        var obv = smart.patient.api.fetchAll({
          type: 'Observation',
          query: {
            code: {
              $or: ['http://loinc.org|8302-2', 'http://loinc.org|8462-4',
                    'http://loinc.org|8480-6', 'http://loinc.org|2085-9',
                    'http://loinc.org|2089-1', 'http://loinc.org|55284-4']
            }
          }
        });

        var conditions = smart.patient.api.fetchAll({ type: 'Condition' });
        var procedures = smart.patient.api.fetchAll({ type: 'Procedure' });
        var encounters = smart.patient.api.fetchAll({ type: 'Encounter' });
        var medications = smart.patient.api.fetchAll({ type: 'MedicationRequest' });
        var careplans = smart.patient.api.fetchAll({ type: 'CarePlan' });
        var allergies = smart.patient.api.fetchAll({ type: 'AllergyIntolerance' });

        $.when(pt, obv, conditions, procedures, encounters, medications, careplans, allergies).fail(onError);

        $.when(pt, obv, conditions, procedures, encounters, medications, careplans, allergies).done(function(patient, obv, conditions, procedures, encounters, medications, careplans, allergies) {
          // ✅ 调试输出
          console.log("✅ Patient:", patient);
          console.log("✅ Observations:", obv);
          console.log("✅ Conditions:", conditions);
          console.log("✅ Procedures:", procedures);
          console.log("✅ Encounters:", encounters);
          console.log("✅ Medications:", medications);
          console.log("✅ CarePlans:", careplans);
          console.log("✅ Allergies:", allergies);

          // 👇 以下为可视化所需基础字段处理（保留原逻辑）
          var byCodes = smart.byCodes(obv, 'code');
          var gender = patient.gender;
          var fname = patient.name?.[0]?.given?.join(' ') || '';
          var lname = patient.name?.[0]?.family || '';
          var height = byCodes('8302-2');
          var systolicbp = getBloodPressureValue(byCodes('55284-4'),'8480-6');
          var diastolicbp = getBloodPressureValue(byCodes('55284-4'),'8462-4');
          var hdl = byCodes('2085-9');
          var ldl = byCodes('2089-1');

          var p = defaultPatient();
          p.birthdate = patient.birthDate;
          p.gender = gender;
          p.fname = fname;
          p.lname = lname;
          p.height = getQuantityValueAndUnit(height[0]);
          p.systolicbp = systolicbp;
          p.diastolicbp = diastolicbp;
          p.hdl = getQuantityValueAndUnit(hdl[0]);
          p.ldl = getQuantityValueAndUnit(ldl[0]);

          ret.resolve(p);
        });
      } else {
        onError();
      }
    }

    FHIR.oauth2.ready(onReady, onError);
    return ret.promise();
  };

  function defaultPatient(){
    return {
      fname: {value: ''},
      lname: {value: ''},
      gender: {value: ''},
      birthdate: {value: ''},
      height: {value: ''},
      systolicbp: {value: ''},
      diastolicbp: {value: ''},
      ldl: {value: ''},
      hdl: {value: ''},
    };
  }

  function getBloodPressureValue(BPObservations, typeOfPressure) {
    var formattedBPObservations = [];
    BPObservations.forEach(function(observation){
      var BP = observation.component?.find(component =>
        component.code?.coding?.find(coding => coding.code == typeOfPressure)
      );
      if (BP) {
        observation.valueQuantity = BP.valueQuantity;
        formattedBPObservations.push(observation);
      }
    });
    return getQuantityValueAndUnit(formattedBPObservations[0]);
  }

  function getQuantityValueAndUnit(ob) {
    if (ob?.valueQuantity?.value && ob?.valueQuantity?.unit) {
      return ob.valueQuantity.value + ' ' + ob.valueQuantity.unit;
    }
    return undefined;
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
