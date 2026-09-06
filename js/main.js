const ingredients = [];

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

function addIngredient(raw) {
  const name = raw.trim().replace(/,+$/, "");
  if (!name) return;
  if (ingredients.includes(name)) return;
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
      const name = escapeHtml(recipe.name || recipe.title || "추천 메뉴");
      const items = Array.isArray(recipe.ingredients)
        ? recipe.ingredients
        : String(recipe.ingredients || "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
      const ingredients = escapeHtml(items.join(", "));
      const method = escapeHtml(recipe.method || recipe.steps || recipe.summary || "");
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
    ingredients.splice(Number(button.dataset.remove), 1);
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
      errorMessage.textContent = "재료를 1개 이상 입력해주세요";
      setView("error");
      return;
    }

    const payload = {
      ingredients: [...ingredients],
      servings: document.getElementById("servings").value,
      time: document.getElementById("cook-time").value,
      taste: document.getElementById("taste").value,
    };

    submitBtn.disabled = true;
    setView("loading");

    try {
      const response = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "recommend-failed");
      }

      const recipes = data.recipes || [];
      if (recipes.length === 0) {
        throw new Error("empty");
      }
      renderRecipes(recipes);
    } catch (error) {
      errorMessage.textContent =
        error.message && error.message !== "empty" && error.message !== "recommend-failed"
          ? error.message
          : "잠시 후 다시 시도해주세요";
      setView("error");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

init();
