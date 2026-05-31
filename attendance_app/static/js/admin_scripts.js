// attendance_app/static/js/admin_scripts.js
// Dashboard filtering logic — period buttons & AJAX data refresh

document.addEventListener('DOMContentLoaded', function () {

    // ── Element refs ───────────────────────────────────
    const filterButtons             = document.querySelectorAll('.filter-button');
    const totalAttendanceHoursCard  = document.getElementById('totalAttendanceHoursCard');
    const totalOvertimeHoursCard    = document.getElementById('totalOvertimeHoursCard');
    const totalAbsenteesCard        = document.getElementById('totalAbsenteesCard');
    const topAbsenteesList          = document.getElementById('topAbsenteesList');
    const topMaxAttendanceList      = document.getElementById('topMaxAttendanceList');
    const topOvertimeList           = document.getElementById('topOvertimeList');
    const topAbsenteesPeriodDisplay     = document.getElementById('topAbsenteesPeriodDisplay');
    const topMaxAttendancePeriodDisplay = document.getElementById('topMaxAttendancePeriodDisplay');
    const topOvertimePeriodDisplay      = document.getElementById('topOvertimePeriodDisplay');

    // ── Helper: update active button state ─────────────
    function setActiveButton(activePeriod) {
        filterButtons.forEach(btn => {
            const isActive = btn.dataset.period === activePeriod;
            btn.classList.toggle('active', isActive);
            // Remove any legacy colour classes from old code
            btn.classList.remove('bg-red-600', 'bg-primary-blue', 'text-white',
                                 'bg-white', 'text-\\[\\#417893\\]',
                                 'hover:bg-red-100', 'hover:text-red-600');
        });
    }

    // ── Helper: skeleton loader for lists ──────────────
    function showListSkeleton(listEl) {
        if (!listEl) return;
        listEl.innerHTML = `
            <li style="padding:.5rem 0;border-bottom:1px solid var(--clr-border);">
                <div class="skeleton skeleton-text" style="width:65%"></div>
                <div class="skeleton skeleton-text" style="width:30%"></div>
            </li>
            <li style="padding:.5rem 0;border-bottom:1px solid var(--clr-border);">
                <div class="skeleton skeleton-text" style="width:70%"></div>
                <div class="skeleton skeleton-text" style="width:25%"></div>
            </li>
            <li style="padding:.5rem 0;">
                <div class="skeleton skeleton-text" style="width:55%"></div>
                <div class="skeleton skeleton-text" style="width:35%"></div>
            </li>`;
    }

    // ── Helper: update a card stat number ──────────────
    function updateCardStat(cardEl, newValue) {
        if (!cardEl) return;
        const h3 = cardEl.querySelector('h3');
        if (!h3) return;
        // Fade out → update → fade in
        h3.style.transition = 'opacity 0.2s';
        h3.style.opacity    = '0';
        setTimeout(() => {
            h3.textContent  = newValue;
            h3.style.opacity = '1';
        }, 200);
    }

    // ── Main update function ───────────────────────────
    async function updateDashboardData(period) {
        setActiveButton(period);

        // Show skeleton loaders
        showListSkeleton(topAbsenteesList);
        showListSkeleton(topMaxAttendanceList);
        showListSkeleton(topOvertimeList);

        try {
            const response = await fetch(`/attendance/get-dashboard-data/?period=${encodeURIComponent(period)}`);

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            const data = await response.json();

            // Update stat cards with animation
            updateCardStat(totalAttendanceHoursCard,
                `${data.total_attendance_hours_all ?? '—'} hrs`);
            updateCardStat(totalOvertimeHoursCard,
                `${data.total_overtime_all ?? '—'} hrs`);
            updateCardStat(totalAbsenteesCard,
                data.total_absentees_count ?? '—');

            // Update list HTML
            if (topAbsenteesList)      topAbsenteesList.innerHTML      = data.top_5_absentees_html       || '<li class="py-3 text-center" style="color:var(--clr-text-muted);">No data</li>';
            if (topMaxAttendanceList)  topMaxAttendanceList.innerHTML  = data.top_5_max_attendance_html  || '<li class="py-3 text-center" style="color:var(--clr-text-muted);">No data</li>';
            if (topOvertimeList)       topOvertimeList.innerHTML       = data.top_5_overtime_html        || '<li class="py-3 text-center" style="color:var(--clr-text-muted);">No data</li>';

            // Update period label in section headers
            const label = period.charAt(0).toUpperCase() + period.slice(1);
            if (topAbsenteesPeriodDisplay)      topAbsenteesPeriodDisplay.textContent      = label;
            if (topMaxAttendancePeriodDisplay)  topMaxAttendancePeriodDisplay.textContent  = label;
            if (topOvertimePeriodDisplay)       topOvertimePeriodDisplay.textContent       = label;

        } catch (error) {
            console.error('Dashboard fetch error:', error);
            window.showToast?.(`Failed to refresh dashboard: ${error.message}`, 'error');

            // Restore lists to show error state
            const errMsg = '<li class="py-3 text-center" style="color:var(--clr-error);">Could not load data</li>';
            if (topAbsenteesList)     topAbsenteesList.innerHTML     = errMsg;
            if (topMaxAttendanceList) topMaxAttendanceList.innerHTML = errMsg;
            if (topOvertimeList)      topOvertimeList.innerHTML      = errMsg;
        }
    }

    // ── Attach click listeners ─────────────────────────
    filterButtons.forEach(button => {
        button.addEventListener('click', function () {
            updateDashboardData(this.dataset.period);
        });
    });

});
