let timeChart = new Chart('timechart', {
  type: 'line',
  data: {
    labels: plotX.slice(),
    datasets: [
      {
        label: 'Expenses',
        data: expensesY,
        borderColor: 'rgba(255, 100, 100, 0.5)',
        backgroundColor: 'rgba(255, 100, 100, 0.1)'
      },
      {
        label: 'Income',
        data: incomeY,
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

$("#slider-range").slider({
  orientation: "horizontal",
  range: true,
  min: 0,
  max: plotX.length - 1,
  values: [0, plotX.length - 1],
  step: 1,
  slide: function(event, ui) {
    $("#range-text1").val(plotX[ui.values[0]]);
    $("#range-text2").val(plotX[ui.values[1]]);
    timeChart.data.labels = plotX.slice(
      ui.values[0],
      ui.values[1] + 1
    );
    timeChart.data.datasets.forEach(dataset => {
      switch (dataset.label) {
      case "Expenses":
        dataset.data = expensesY.slice(
          ui.values[0],
          ui.values[1] + 1
        );
        break;
      case "Income":
        dataset.data = incomeY.slice(
          ui.values[0],
          ui.values[1] + 1
        );
        break;
      }
    });
    timeChart.update();

    const expensesInPeriod = sumAccounts(
      plotX[ui.values[0]],
      plotX[ui.values[1]]
    );
    pieChart.data.labels = Object.keys(expensesInPeriod);
    pieChart.data.datasets.forEach(dataset =>
                                   dataset.data = Object.values(expensesInPeriod));
    pieChart.update();
  }
});
$("#range-text1").val(
  plotX[$("#slider-range").slider("values", 0)]);
$("#range-text2").val(
  plotX[$("#slider-range").slider("values", 1)]);


const expenses =
      _.chain(expensesFlat)
      .groupBy('date')
      .mapObject(obj =>
                 _.chain(obj)
                 .groupBy('account')
                 .mapObject(obj => obj[0].amount)
                 .value())
      .value();

const sumAccounts = function (dateStart, dateEnd) {
  const groups = Object.entries(expenses)
        .flatMap(([k,v]) => ((dateStart <= k && k <= dateEnd) ? [v] : []));
  return _.chain(groups)
    .map(_.pairs)
    .flatten(true)
    .groupBy(_.first)
    .mapObject(x => _.chain(x).map(_.last).reduce((a, b) => a + b).value())
    .mapObject(x => x.toFixed(2))
    .value();
}
const expensesInPeriod = sumAccounts(
  plotX[$("#slider-range").slider("values", 0)],
  plotX[$("#slider-range").slider("values", 1)]
);

let pieChart = new Chart('piechart', {
  type: 'pie',
  data: {
    labels: Object.keys(expensesInPeriod),
    datasets: [{
      label: 'Expenses',
      data: Object.values(expensesInPeriod),
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
