"use strict";

let timeChart = new Chart('timechart', {
  type: 'line',
  data: {
    labels: dates.slice(),
    datasets: [
      {
        label: expensesFilter,
        data: expensesTotals,
        borderColor: 'rgba(255, 100, 100, 0.5)',
        backgroundColor: 'rgba(255, 100, 100, 0.1)'
      },
      {
        label: 'Income',
        data: incomeTotals,
        borderColor: 'rgba(50, 200, 50, 1)',
        backgroundColor: 'rgba(50, 200, 50, 0.1)'
      }
    ]
  },
  options: {
    scales: {
      yAxes: [{
        ticks: {
          beginAtZero: true
        }
      }]
    }
  }
});

const showAllPiechartLabels = function () {
  pieChart.getDatasetMeta(0).data.forEach(x => x.hidden = false);
}

const updateTimeRange = function (rangeStart, rangeEnd) {
  timeChart.data.labels = dates.slice(
    rangeStart,
    rangeEnd + 1
  );
  timeChart.data.datasets.forEach(dataset => {
    switch (dataset.label) {
    case "Expenses":
      dataset.data = expensesTotals.slice(
        rangeStart,
        rangeEnd + 1
      );
      break;
    case "Income":
      dataset.data = incomeTotals.slice(
        rangeStart,
        rangeEnd + 1
      );
      break;
    }
  });
  timeChart.update();

  const expensesInPeriod = sortExpenses(
    sumAccounts(
      dates[rangeStart],
      dates[rangeEnd]
    )
  );
  const oldLabels = pieChart.data.labels;
  const newLabels = _.map(expensesInPeriod, _.first);
  pieChart.data.labels = newLabels;
  if (!_.isEqual(oldLabels, newLabels)) {
    showAllPiechartLabels();
  }
  pieChart.data.datasets.forEach(
    dataset =>
      dataset.data = _.map(expensesInPeriod, _.last));
  pieChart.update();
};

$("#slider-range").slider({
  orientation: "horizontal",
  range: true,
  min: 0,
  max: dates.length - 1,
  values: [0, dates.length - 1],
  step: 1,
  slide: function (event, ui) {
    $("#range-select1").val(ui.values[0]);
    $("#range-select2").val(ui.values[1]);
    updateTimeRange(...ui.values);
  }
});

$("#range-select1").val(
  $("#slider-range").slider("values", 0));
$("#range-select2").val(
  $("#slider-range").slider("values", 1));

const updateCharts = function () {
  updateTimeRange(...$("#slider-range").slider("values"));
};
document.querySelectorAll('input[name="chart-sort"]').forEach(
  x => x.addEventListener('click', updateCharts)
);

$("#range-select1").change(
  function () {
    $("#slider-range").slider("values", 0, $(this).val());
    updateCharts();
  }
);
$("#range-select2").change(
  function () {
    $("#slider-range").slider("values", 1, $(this).val());
    updateCharts();
  }
);

const sortExpenses = function (expensesInPeriod) {
  const order = document.querySelector('input[name="chart-sort"]:checked').value;
  if (order == 'value') {
    return expensesInPeriod.sort(
      (a, b) => _.last(b) - _.last(a)
    );
  } else if (order == 'label') {
    return expensesInPeriod;
  }
}

const expenses =
      _.chain(expensesFlat)
      .groupBy('account')
      .mapValues(obj =>
                 _.chain(obj)
                 .groupBy('date')
                 .mapValues(obj => obj[0].amount)
                 .value())
      .value();

const sumAccounts = function (dateStart, dateEnd) {
  return _.chain(expenses)
    .mapValues(x =>
               _.chain(x)
               .toPairs()
               .filter(([k,v]) => (dateStart <= k && k <= dateEnd))
               .map(_.last)
               .reduce((a, b) => a + b, 0)
               .value())
    .mapValues(x => x.toFixed(2))
    .toPairs()
    .sort()
    .value();
}
const expensesInPeriod = sortExpenses(
  sumAccounts(
    dates[$("#slider-range").slider("values", 0)],
    dates[$("#slider-range").slider("values", 1)]
  )
);

let pieChart = new Chart('piechart', {
  type: 'pie',
  data: {
    labels: _.map(expensesInPeriod, _.first),
    datasets: [{
      label: 'Expenses',
      data: _.map(expensesInPeriod, _.last),
      backgroundColor: [
        '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4',
        '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff',
        '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1',
        '#000075', '#808080', '#cccccc', '#000000', '#00ff00', '#0000ff'
      ]
    }]
  },
  options: {
    cutoutPercentage: 30,
    layout: {
      padding: {
        top: 50
      }
    },
    legend: {
      position: 'right'
    }
  }
});
