
document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const menuButton = document.getElementById("menuButton");
    const navigationLinks = document.querySelectorAll(".nav-link");
    const searchInput = document.getElementById("dashboardSearch");

    // --------------------------------------------------
    // MOBILE SIDEBAR
    // --------------------------------------------------

    function closeSidebar() {
        if (!sidebar || !menuButton) return;

        sidebar.classList.remove("open");
        menuButton.setAttribute("aria-expanded", "false");
    }

    function toggleSidebar() {
        if (!sidebar || !menuButton) return;

        const isOpen = sidebar.classList.toggle("open");
        menuButton.setAttribute("aria-expanded", String(isOpen));
    }

    if (sidebar && menuButton) {
        menuButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleSidebar();
        });

        document.addEventListener("click", (event) => {
            if (
                sidebar.classList.contains("open") &&
                !sidebar.contains(event.target) &&
                !menuButton.contains(event.target)
            ) {
                closeSidebar();
            }
        });

        window.addEventListener("resize", () => {
            if (window.innerWidth > 760) {
                closeSidebar();
            }
        });
    }

    // --------------------------------------------------
    // NAVIGATION
    // --------------------------------------------------

    function setActiveNavigation(activeLink) {
        navigationLinks.forEach((link) => {
            link.classList.toggle("active", link === activeLink);
        });
    }

    navigationLinks.forEach((link) => {
        link.addEventListener("click", () => {
            const href = link.getAttribute("href");

            // Only update active state for in-page navigation.
            // Normal Flask routes should navigate normally.
            if (href && href.startsWith("#")) {
                setActiveNavigation(link);
            }

            closeSidebar();
        });
    });

    // --------------------------------------------------
    // ACTIVE SECTION WHILE SCROLLING
    // --------------------------------------------------

    const sections = document.querySelectorAll(
        "main[id], .content-section[id], .analytics-grid[id], " +
        ".lower-grid[id], section[id], article[id], aside[id]"
    );

    if ("IntersectionObserver" in window && sections.length > 0) {
        const observer = new IntersectionObserver(
            (entries) => {
                const visibleSections = entries
                    .filter((entry) => entry.isIntersecting)
                    .sort(
                        (a, b) =>
                            b.intersectionRatio - a.intersectionRatio
                    );

                if (visibleSections.length === 0) return;

                const currentId = visibleSections[0].target.id;

                const matchingLink = Array.from(navigationLinks).find(
                    (link) =>
                        link.getAttribute("href") === `#${currentId}`
                );

                if (matchingLink) {
                    setActiveNavigation(matchingLink);
                }
            },
            {
                rootMargin: "-18% 0px -65% 0px",
                threshold: [0, 0.15, 0.35, 0.6]
            }
        );

        sections.forEach((section) => observer.observe(section));
    }

    // --------------------------------------------------
    // DASHBOARD SEARCH
    // Filters visible dashboard table rows and highlights
    // matching dashboard content.
    // --------------------------------------------------

    if (searchInput) {
        const searchableRows = document.querySelectorAll(
            ".table-container tbody tr, " +
            ".table-wrapper tbody tr"
        );

        const searchableCards = document.querySelectorAll(
            ".quality-alert-card, .approval-item"
        );

        let searchMessage = null;

        function ensureSearchMessage() {
            if (searchMessage) return;

            searchMessage = document.createElement("p");
            searchMessage.className = "search-feedback";
            searchMessage.setAttribute("role", "status");
            searchMessage.style.color = "#a0aec1";
            searchMessage.style.fontSize = "11px";
            searchMessage.style.margin = "10px 0";

            searchInput.closest(".topbar-search")?.insertAdjacentElement(
                "afterend",
                searchMessage
            );
        }

        searchInput.addEventListener("input", () => {
            const query = searchInput.value.trim().toLowerCase();
            let matches = 0;

            searchableRows.forEach((row) => {
                const isMatch = row.textContent
                    .toLowerCase()
                    .includes(query);

                row.hidden = Boolean(query) && !isMatch;

                if (!query || isMatch) {
                    matches += 1;
                }
            });

            searchableCards.forEach((card) => {
                const isMatch = card.textContent
                    .toLowerCase()
                    .includes(query);

                card.hidden = Boolean(query) && !isMatch;

                if (query && isMatch) {
                    matches += 1;
                }
            });

            if (query) {
                ensureSearchMessage();

                if (searchMessage) {
                    searchMessage.textContent = matches
                        ? `${matches} matching item(s) in the displayed dashboard.`
                        : "No matching items in the displayed dashboard.";
                }
            } else if (searchMessage) {
                searchMessage.textContent = "";
            }
        });
    }

    // --------------------------------------------------
    // ACCESSIBLE TABLE ROW VISIBILITY
    // --------------------------------------------------

    document.querySelectorAll("tr[hidden]").forEach((row) => {
        row.hidden = true;
    });

    // --------------------------------------------------
    // KEYBOARD ACCESSIBILITY
    // --------------------------------------------------

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSidebar();

            if (searchInput && document.activeElement === searchInput) {
                searchInput.value = "";
                searchInput.dispatchEvent(new Event("input"));
                searchInput.blur();
            }
        }
    });
});
