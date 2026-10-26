(function () {
    "use strict";

    var form = document.getElementById("searchForm");
    var input = document.getElementById("movieInput");
    var clearBtn = document.getElementById("clearBtn");
    var chipsBox = document.getElementById("recentChips");
    var skeletons = document.getElementById("skeletons");
    var grid = document.getElementById("movieGrid");
    var themeBtn = document.getElementById("themeToggle");

    var RECENT_KEY = "recentMovies";
    var MAX_RECENT = 5;

    /* ---------- safe localStorage helpers ---------- */
    function load(key, fallback) {
        try {
            var raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : fallback;
        } catch (e) {
            return fallback;
        }
    }

    function save(key, value) {
        try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
    }

    /* ---------- theme toggle ---------- */
    themeBtn.addEventListener("click", function () {
        var root = document.documentElement;
        var current = root.getAttribute("data-theme");
        if (!current) {
            current = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }
        var next = current === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (e) {}
    });

    /* ---------- clear button ---------- */
    function syncClear() { clearBtn.hidden = input.value.length === 0; }

    input.addEventListener("input", syncClear);
    clearBtn.addEventListener("click", function () {
        input.value = "";
        syncClear();
        input.focus();
    });
    syncClear();

    /* ---------- recent searches ---------- */
    function renderRecent() {
        var recent = load(RECENT_KEY, []);
        chipsBox.innerHTML = "";
        if (!recent.length) {
            chipsBox.hidden = true;
            return;
        }
        recent.forEach(function (name) {
            var chip = document.createElement("button");
            chip.type = "button";
            chip.className = "chip";
            chip.textContent = name;
            chip.addEventListener("click", function () {
                input.value = name;
                form.requestSubmit();
            });
            chipsBox.appendChild(chip);
        });
        chipsBox.hidden = false;
    }

    function remember(name) {
        name = name.trim();
        if (!name) return;
        var recent = load(RECENT_KEY, []).filter(function (n) {
            return n.toLowerCase() !== name.toLowerCase();
        });
        recent.unshift(name);
        save(RECENT_KEY, recent.slice(0, MAX_RECENT));
    }

    renderRecent();

    /* ---------- submit: loading state ---------- */
    form.addEventListener("submit", function () {
        remember(input.value);
        form.classList.add("is-loading");
        if (grid) grid.hidden = true;
        var toolbar = document.getElementById("toolbar");
        if (toolbar) toolbar.hidden = true;
        if (skeletons) skeletons.hidden = false;
    });

    // Restore the page if the user returns with the browser's Back button
    window.addEventListener("pageshow", function () {
        form.classList.remove("is-loading");
        if (skeletons) skeletons.hidden = true;
        if (grid) grid.hidden = false;
        var toolbar = document.getElementById("toolbar");
        if (toolbar) toolbar.hidden = false;
    });

    /* ---------- keyboard shortcut: "/" focuses search ---------- */
    document.addEventListener("keydown", function (e) {
        var tag = (document.activeElement && document.activeElement.tagName) || "";
        if (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA") {
            e.preventDefault();
            input.focus();
            input.select();
        }
    });

    /* ---------- helpers for movie data ---------- */
    // Genres may arrive as "Action|Adventure", "Action, Adventure" or "Action Adventure".
    function parseGenres(text) {
        if (!text) return [];
        var parts = /[|,;]/.test(text) ? text.split(/[|,;]/) : text.split(/\s+/);
        return parts
            .map(function (g) { return g.trim(); })
            .filter(function (g) { return g && g !== "(no genres listed)" && g.toLowerCase() !== "none"; });
    }

    function toNumber(text) {
        var n = parseFloat(text);
        return isNaN(n) ? 0 : n;
    }

    function genreTag(name) {
        var s = document.createElement("span");
        s.className = "genre-tag";
        s.textContent = name;
        return s;
    }

    /* ---------- result cards ---------- */
    var cards = grid ? Array.prototype.slice.call(grid.querySelectorAll(".movie-card")) : [];
    var activeGenre = null;

    cards.forEach(function (card) {
        // match ring: accepts 0–1 (0.93) or 0–100 (93.4)
        var ring = card.querySelector(".ring");
        var raw = parseFloat(card.getAttribute("data-sim"));
        if (ring && !isNaN(raw)) {
            var pct = raw <= 1 ? raw * 100 : raw;
            pct = Math.max(0, Math.min(100, pct));
            ring.style.setProperty("--target", pct.toFixed(1));
            ring.querySelector(".ring__value").textContent = Math.round(pct) + "%";
            ring.setAttribute("aria-label", "Match " + Math.round(pct) + " percent");
            card.dataset.pct = pct;
        }

        // genre tags (first three on the card)
        var genres = parseGenres(card.getAttribute("data-genres"));
        card.dataset.genreList = JSON.stringify(genres);
        var box = card.querySelector(".movie-card__genres");
        genres.slice(0, 3).forEach(function (g) { box.appendChild(genreTag(g)); });
    });

    /* ---------- genre filter chips ---------- */
    var filterBox = document.getElementById("genreFilters");

    function buildFilters() {
        if (!filterBox) return;
        var counts = {};
        cards.forEach(function (card) {
            JSON.parse(card.dataset.genreList || "[]").forEach(function (g) {
                counts[g] = (counts[g] || 0) + 1;
            });
        });

        var names = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
        if (names.length < 2) return;

        names.slice(0, 8).forEach(function (g) {
            var chip = document.createElement("button");
            chip.type = "button";
            chip.className = "chip";
            chip.textContent = g;
            chip.setAttribute("aria-pressed", "false");
            chip.addEventListener("click", function () {
                activeGenre = activeGenre === g ? null : g;
                Array.prototype.forEach.call(filterBox.children, function (c) {
                    var on = c.textContent === activeGenre;
                    c.classList.toggle("is-active", on);
                    c.setAttribute("aria-pressed", on ? "true" : "false");
                });
                applyFilter();
            });
            filterBox.appendChild(chip);
        });
    }

    function applyFilter() {
        cards.forEach(function (card) {
            var list = JSON.parse(card.dataset.genreList || "[]");
            card.hidden = !!activeGenre && list.indexOf(activeGenre) === -1;
        });
    }

    buildFilters();

    /* ---------- sorting ---------- */
    var sorters = {
        match: function (a, b) { return toNumber(b.dataset.pct) - toNumber(a.dataset.pct) || a.dataset.order - b.dataset.order; },
        rating: function (a, b) { return toNumber(b.dataset.rating) - toNumber(a.dataset.rating); },
        year: function (a, b) { return toNumber(b.dataset.year) - toNumber(a.dataset.year); }
    };

    document.querySelectorAll(".segmented__btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            document.querySelectorAll(".segmented__btn").forEach(function (b) {
                b.classList.toggle("is-active", b === btn);
            });
            var fn = sorters[btn.getAttribute("data-sort")];
            cards.slice().sort(fn).forEach(function (card) { grid.appendChild(card); });
        });
    });

    /* ---------- details dialog ---------- */
    var dlg = document.getElementById("detailsDialog");

    if (dlg && typeof dlg.showModal === "function") {
        document.getElementById("dlgClose").addEventListener("click", function () { dlg.close(); });
        dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close(); });

        cards.forEach(function (card) {
            card.querySelector(".details-btn").addEventListener("click", function () {
                document.getElementById("dlgTitle").textContent = card.dataset.title;

                var bits = [];
                if (card.dataset.year) bits.push(card.dataset.year);
                if (card.dataset.rating) bits.push("★ " + card.dataset.rating);
                if (card.dataset.pct) bits.push(Math.round(card.dataset.pct) + "% match");
                document.getElementById("dlgMeta").textContent = bits.join("  •  ");

                var gBox = document.getElementById("dlgGenres");
                gBox.innerHTML = "";
                JSON.parse(card.dataset.genreList || "[]").forEach(function (g) {
                    gBox.appendChild(genreTag(g));
                });

                document.getElementById("dlgText").textContent =
                    card.dataset.overview || "No description is available for this movie.";

                dlg.showModal();
            });
        });
    } else {
        document.querySelectorAll(".details-btn").forEach(function (b) { b.hidden = true; });
    }

    /* ---------- reveal rings and bars once, when visible ---------- */
    var targets = document.querySelectorAll(".ring, .bar__fill");

    function reveal(el) { el.classList.add("is-ready"); }

    if ("IntersectionObserver" in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    reveal(entry.target);
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });
        targets.forEach(function (el) { io.observe(el); });
    } else {
        targets.forEach(reveal);
    }

    /* ---------- count-up for the big numbers ---------- */
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    document.querySelectorAll("[data-count]").forEach(function (el) {
        var end = parseFloat(String(el.getAttribute("data-count")).replace(/,/g, ""));
        if (isNaN(end)) return;
        if (reduce) {
            el.textContent = end.toLocaleString();
            return;
        }

        var start = null;
        var duration = 900;

        function tick(ts) {
            if (start === null) start = ts;
            var t = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - t, 3);
            el.textContent = Math.round(end * eased).toLocaleString();
            if (t < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    });
})();