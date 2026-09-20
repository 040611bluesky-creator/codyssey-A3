const ingredients = [];

const MAX_INGREDIENTS_LENGTH = 1000;
const TOO_LONG_INGREDIENTS_MESSAGE =
  "재료 입력은 1000자 이내로 입력해주세요";

const form = document.getElementById("recommend-form");
const input = document.getElementById("ingredient-input");
const chips = document.getElementById("ingredient-chips");
const submitBtn = document.getElementById("submit-btn");
const emptyState = document.getElementById("result-empty");
const loadingState = document.getElementById("result-loading");
const errorState = document.getElementById("result-error");
const errorMessage = document.getElementById("error-message");
const recipeList = document.getElementById("recipe-list");

function renderChips() {
  chips.innerHTML = ingredients
    .map(
      (name, index) => `
        <li class="chip">
          <span>${name}</span>
          <button type="button" data-remove="${index}" aria-label="${name} 삭제">×</button>
        </li>
      `
    )
    .join("");
}

function getIngredientsLength() {
  return ingredients.reduce(
    (total, name) => total + name.length,
    0
  );
}

function addIngredient(raw) {
  const name = raw.trim().replace(/,+$/, "");

  if (!name) return;

  if (ingredients.includes(name)) return;

  const currentLength = getIngredientsLength();

  if (currentLength + name.length > MAX_INGREDIENTS_LENGTH) {
    errorMessage.textContent = TOO_LONG_INGREDIENTS_MESSAGE;
    setView("error");
    return;
  }

  ingredients.push(name);
  renderChips();
}

function setView(view) {
  emptyState.classList.toggle("hidden", view !== "empty");
  loadingState.classList.toggle("hidden", view !== "loading");
  errorState.classList.toggle("hidden", view !== "error");
  recipeList.classList.toggle("hidden", view !== "recipes");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderRecipes(recipes) {
  recipeList.innerHTML = recipes
    .map((recipe) => {
      const name = escapeHtml(
        recipe.name || recipe.title || "추천 메뉴"
      );

      const items = Array.isArray(recipe.ingredients)
        ? recipe.ingredients
        : String(recipe.ingredients || "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);

      const ingredients = escapeHtml(items.join(", "));

      const method = escapeHtml(
        recipe.method ||
          recipe.steps ||
          recipe.summary ||
          ""
      );

      return `
        <li class="recipe-card">
          <h3>${name}</h3>
          <p class="recipe-meta">${ingredients}</p>
          <p>${method}</p>
        </li>
      `;
    })
    .join("");

  setView("recipes");
}

function initThemeToggle() {
  const toggleBtn = document.getElementById("theme-toggle");

  if (!toggleBtn) return;

  const root = document.documentElement;

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    toggleBtn.textContent =
      theme === "dark" ? "☀️" : "🌙";
  }

  let saved = "light";

  try {
    saved = localStorage.getItem("theme") || "light";
  } catch (error) {
    saved = "light";
  }

  applyTheme(saved);

  toggleBtn.addEventListener("click", () => {
    const next =
      root.getAttribute("data-theme") === "dark"
        ? "light"
        : "dark";

    applyTheme(next);

    try {
      localStorage.setItem("theme", next);
    } catch (error) {
      // 저장 실패해도 화면 전환은 정상 동작
    }
  });
}

function init() {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();

      addIngredient(input.value);

      input.value = "";
    }
  });

  chips.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");

    if (!button) return;

    ingredients.splice(
      Number(button.dataset.remove),
      1
    );

    renderChips();
  });

  document.querySelectorAll(".chip-btn").forEach((button) => {
    button.addEventListener("click", () => {
      addIngredient(button.dataset.ingredient);
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (ingredients.length === 0) {
      errorMessage.textContent =
        "재료를 1개 이상 입력해주세요";

      setView("error");
      return;
    }

    // API 요청 전에 전체 입력 길이를 한 번 더 검증
    const totalLength = getIngredientsLength();

    if (totalLength > MAX_INGREDIENTS_LENGTH) {
      errorMessage.textContent =
        TOO_LONG_INGREDIENTS_MESSAGE;

      setView("error");
      return;
    }

    const payload = {
      ingredients: [...ingredients],
      servings:
        document.getElementById("servings").value,
      time:
        document.getElementById("cook-time").value,
      taste:
        document.getElementById("taste").value,
    };

    submitBtn.disabled = true;
    setView("loading");

    try {
      const response = await fetch("/api/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "recommend-failed"
        );
      }

      const recipes = data.recipes || [];

      if (recipes.length === 0) {
        throw new Error("empty");
      }

      renderRecipes(recipes);
    } catch (error) {
      errorMessage.textContent =
        error.message &&
        error.message !== "empty" &&
        error.message !== "recommend-failed"
          ? error.message
          : "잠시 후 다시 시도해주세요";

      setView("error");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

initThemeToggle();
init();