// Ensure Chart.js and jQuery are loaded BEFORE this script
// <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
// <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

// This `reportData` variable is expected to be parsed from Django's context in reports.html
// The keys here MUST match what's in your admin_views.py's reports_view context.
/*
Expected `reportData` structure based on admin_views.py:
const reportData = {
    'emotionTrends': { // Matches emotionTrends from Django
        'weekly': { labels: [...], happy: [...], sad: [...], neutral: [...] },
        'monthly': { ... },
        'yearly': { ... }
    },
    'leaveDistribution': { // Matches leaveDistribution from Django
        labels: [...], data: [...]
    },
    'arrivalStats': { // Matches arrivalStats from Django
        'weekly': { labels: [...], on_time: [...], late: [...], early: [...] }, // Added early, though only on_time/late are charted
        'monthly': { ... },
        'yearly': { ... }
    },
    'attendanceTrends': { // Matches attendanceTrends from Django
        'weekly': { labels: [...], present: [...], absent: [...] }, // Changed to present/absent
        'monthly': { ... },
        'yearly': { ... }
    }
};
*/

$(document).ready(function () {
    console.log("📈 reports_scripts.js loaded.");
    console.log("Report Data received:", reportData); // This should now show the correct keys

    // --- Chart Instances ---
    let emotionTrendsChart;
    let leaveDistributionChart;
    let arrivalStatsChart;
    let attendanceTrendsChart;

    // --- Chart.js Global Defaults (for a cleaner look as per the image) ---
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#4b5563'; // Tailwind gray-600 for default text color
    Chart.defaults.borderColor = '#e5e7eb'; // Light gray for grid lines

    // --- Emotion Tracking Trends Chart ---
    function createEmotionTrendsChart(period = 'weekly') {
        const ctx = document.getElementById('emotionTrendsChart').getContext('2d');
        if (emotionTrendsChart) {
            emotionTrendsChart.destroy(); // Destroy existing chart to redraw
        }
        const data = reportData.emotionTrends[period];
        if (!data || !Array.isArray(data.labels) || data.labels.length === 0 ||
            !Array.isArray(data.happy) || !Array.isArray(data.sad) || !Array.isArray(data.neutral)) {
            console.warn(`No valid emotion trends data found for period: ${period}. Skipping chart creation.`);
            return;
        }
        emotionTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Happy',
                        data: data.happy,
                        borderColor: '#8b5cf6', // A vibrant purple/pink, similar to image
                        backgroundColor: 'rgba(139, 92, 246, 0.2)', // Lighter fill for area
                        tension: 0.4, // Smooth curve
                        fill: true, // Fill area under the line
                        pointRadius: 3,
                        pointBackgroundColor: '#8b5cf6',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Sad',
                        data: data.sad,
                        borderColor: '#ef4444', // Red for contrast
                        backgroundColor: 'rgba(239, 68, 68, 0.2)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointBackgroundColor: '#ef4444',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Neutral',
                        data: data.neutral,
                        borderColor: '#3b82f6', // Blue
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointBackgroundColor: '#3b82f6',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Occurrences',
                            color: '#1f2937' // Darker text for titles
                        },
                        grid: {
                            color: '#f3f4f6' // Lighter grid lines
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Period',
                            color: '#1f2937'
                        },
                        grid: {
                            color: '#f3f4f6'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Emotion Trends (${period.charAt(0).toUpperCase() + period.slice(1)})`,
                        font: {
                            size: 18,
                            weight: 'bold'
                        },
                        color: '#1f2937'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#374151', // Legend text color
                            font: {
                                size: 14
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                hover: {
                    mode: 'nearest',
                    intersect: true
                }
            }
        });
        console.log(`Emotion Trends Chart created for ${period}.`);
    }

    // --- Leave Type Distribution Chart (Pie/Doughnut) ---
    function createLeaveDistributionChart() {
        const ctx = document.getElementById('leaveDistributionChart').getContext('2d');
        if (leaveDistributionChart) {
            leaveDistributionChart.destroy();
        }
        const data = reportData.leaveDistribution;
        // Added more robust data check
        if (!data || !Array.isArray(data.labels) || data.labels.length === 0 || !Array.isArray(data.data) || data.data.length === 0) {
            console.warn("No valid leave distribution data found. Skipping chart creation.");
            return;
        }

        // Check if all data values are zero - if so, Chart.js might draw nothing or an empty circle.
        const allDataZero = data.data.every(val => val === 0);
        if (allDataZero) {
            console.warn("All leave distribution data values are zero. Displaying a placeholder chart.");
            // Render a placeholder or message if all data is zero
            // You might want to update your HTML to show a text message instead.
            // For now, setting a very basic dummy chart to show something.
            leaveDistributionChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['No Leaves Recorded'],
                    datasets: [{
                        data: [1], // A small dummy value to make the chart visible
                        backgroundColor: ['#e5e7eb'], // Light gray color
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Leave Type Distribution (No Leaves Recorded)',
                            font: {size: 18, weight: 'bold'},
                            color: '#1f2937'
                        },
                        legend: {display: false},
                        tooltip: {enabled: false}
                    }
                }
            });
            return;
        }


        leaveDistributionChart = new Chart(ctx, {
            type: 'doughnut', // Pie for specific percentages is good
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: [
                        '#8b5cf6', // Purple/Pink
                        '#ef4444', // Red
                        '#3b82f6', // Blue
                        '#10b981', // Emerald green
                        '#f59e0b'  // Amber
                    ],
                    borderColor: '#ffffff', // White border between segments
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Leave Type Distribution',
                        font: {
                            size: 18,
                            weight: 'bold'
                        },
                        color: '#1f2937'
                    },
                    legend: {
                        position: 'right', // Place legend on the right
                        labels: {
                            color: '#374151',
                            font: {
                                size: 14
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed) {
                                    // If total_leaves_taken_all_time is total data, convert to percentage
                                    const totalSum = context.dataset.data.reduce((sum, val) => sum + val, 0);
                                    if (totalSum > 0) {
                                        label += ((context.parsed / totalSum) * 100).toFixed(1) + '%';
                                    } else {
                                        label += context.parsed;
                                    }
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
        console.log("Leave Distribution Chart created.");
    }

    // --- Late Arrivals vs On-Time Stats Chart ---
    function createArrivalStatsChart(period = 'weekly') {
        const ctx = document.getElementById('arrivalStatsChart').getContext('2d');
        if (arrivalStatsChart) {
            arrivalStatsChart.destroy();
        }
        const data = reportData.arrivalStats[period];
        if (!data || !Array.isArray(data.labels) || data.labels.length === 0 ||
            !Array.isArray(data.on_time) || !Array.isArray(data.late)) {
            console.warn(`No valid arrival stats data found for period: ${period}. Skipping chart creation.`);
            return;
        }
        // Changed type to 'line' and updated styling to match Emotion Trends Chart
        arrivalStatsChart = new Chart(ctx, {
            type: 'line', // Changed from 'bar' to 'line'
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'On-Time Arrivals',
                        data: data.on_time,
                        borderColor: '#10b981', // Emerald green, for on-time
                        backgroundColor: 'rgba(16, 185, 129, 0.2)', // Lighter fill
                        tension: 0.4, // Smooth curve
                        fill: true, // Fill area under the line
                        pointRadius: 3,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Late Arrivals',
                        data: data.late,
                        borderColor: '#f59e0b', // Amber, for late
                        backgroundColor: 'rgba(245, 158, 11, 0.2)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointBackgroundColor: '#f59e0b',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Employees',
                            color: '#1f2937'
                        },
                        grid: {
                            color: '#f3f4f6'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Period',
                            color: '#1f2937'
                        },
                        grid: {
                            color: '#f3f4f6'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Arrival Statistics (${period.charAt(0).toUpperCase() + period.slice(1)})`,
                        font: {
                            size: 18,
                            weight: 'bold'
                        },
                        color: '#1f2937'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#374151',
                            font: {
                                size: 14
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                hover: {
                    mode: 'nearest',
                    intersect: true
                }
            }
        });
        console.log(`Arrival Stats Chart created for ${period}.`);
    }

    // --- Attendance Trends Over Time Chart ---
    function createAttendanceTrendsChart(period = 'weekly') {
        const ctx = document.getElementById('attendanceTrendsChart').getContext('2d');
        if (attendanceTrendsChart) {
            attendanceTrendsChart.destroy();
        }
        const data = reportData.attendanceTrends[period];
        // Added more robust data check
        if (!data || !Array.isArray(data.labels) || data.labels.length === 0 ||
            !Array.isArray(data.present) || !Array.isArray(data.absent)) {
            console.warn(`No valid attendance trends data found for period: ${period}. Skipping chart creation.`);
            return;
        }
        attendanceTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Present',
                        data: data.present,
                        borderColor: '#10b981', // Emerald green, for presence
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Absent',
                        data: data.absent,
                        borderColor: '#f59e0b', // Amber, for absence
                        backgroundColor: 'rgba(245, 158, 11, 0.2)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 3,
                        pointBackgroundColor: '#f59e0b',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Employees',
                            color: '#1f2937'
                        },
                        grid: {
                            color: '#f3f4f6'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Attendance Trends (${period.charAt(0).toUpperCase() + period.slice(1)})`,
                        font: {
                            size: 18,
                            weight: 'bold'
                        },
                        color: '#1f2937'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#374151',
                            font: {
                                size: 14
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                hover: {
                    mode: 'nearest',
                    intersect: true
                }
            }
        });
        console.log(`Attendance Trends Chart created for ${period}.`);
    }

    $(document).ready(function () {
        console.log("📈 reports_scripts.js loaded.");
        console.log("Report Data received:", reportData);

        // --- Apply styles to active button and reset others ---
        function applyActiveStyle(button) {
            const siblings = button.parentElement.querySelectorAll('button');
            siblings.forEach(btn => {
                if (btn === button) {
                    // Active style
                    btn.style.background = 'linear-gradient(45deg, #ef4444, #ef4444)';
                } else {
                    // Inactive style
                    btn.style.background = 'linear-gradient(45deg, #555555, #555555)';
                }

                btn.style.color = 'white';
                btn.style.padding = '12px';
                btn.style.border = 'none';
                btn.style.fontWeight = '600';
                btn.style.textTransform = 'uppercase';
                btn.style.cursor = 'pointer';
                btn.style.transition = 'background 0.4s ease-in-out, color 0.3s ease';
            });
        }

        // --- Chart render dispatch ---
        function renderChart(chartType, period) {
            switch (chartType) {
                case 'emotion':
                    createEmotionTrendsChart(period);
                    break;
                case 'arrival':
                    createArrivalStatsChart(period);
                    break;
                case 'attendance':
                    createAttendanceTrendsChart(period);
                    break;
                default:
                    console.warn(`Unknown chart type: ${chartType}`);
            }
        }

        // --- Generic event listener for all chart period buttons ---
        $('.report-btn').on('click', function () {
            applyActiveStyle(this);
            const chartType = this.dataset.chart;     // 'emotion', 'arrival', 'attendance'
            const period = this.dataset.period;        // 'weekly', 'monthly', 'yearly'
            renderChart(chartType, period);
        });

        // --- Initial Chart Rendering ---
        if (reportData) {
            if (reportData.emotionTrends) createEmotionTrendsChart('weekly');
            if (reportData.leaveDistribution) createLeaveDistributionChart();
            if (reportData.arrivalStats) createArrivalStatsChart('weekly');
            if (reportData.attendanceTrends) createAttendanceTrendsChart('weekly');
        } else {
            console.warn("reportData is undefined or null.");
        }

        // Trigger default buttons to apply styles on load
        $('#emotionWeeklyBtn, #arrivalWeeklyBtn, #attendanceWeeklyBtn').trigger('click');
    });
});


