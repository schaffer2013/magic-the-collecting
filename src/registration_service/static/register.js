const imageInput = document.querySelector("#image-input");
const preview = document.querySelector("#preview");
const editor = document.querySelector("#editor");
const overlay = document.querySelector("#overlay");
const polygon = document.querySelector("#polygon");
const handles = document.querySelector("#handles");
const useBox = document.querySelector("#use-box");
const status = document.querySelector("#status");
const form = document.querySelector("#registration-form");
const defaultKey = "magicCollecting.defaultBoundingBox";

let points = JSON.parse(localStorage.getItem(defaultKey) || "null") || [
  [0.08, 0.08], [0.92, 0.08], [0.92, 0.92], [0.08, 0.92],
];

function renderPoints() {
  polygon.setAttribute("points", points.map(([x, y]) => `${x},${y}`).join(" "));
  handles.innerHTML = "";
  points.forEach(([x, y], index) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", "0.035");
    circle.dataset.index = index;
    handles.appendChild(circle);
  });
}

function imagePoint(event) {
  const rect = overlay.getBoundingClientRect();
  return [
    Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
    Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
  ];
}

overlay.addEventListener("pointerdown", (event) => {
  if (event.target.tagName !== "circle") return;
  const index = Number(event.target.dataset.index);
  overlay.setPointerCapture(event.pointerId);
  const move = (moveEvent) => {
    points[index] = imagePoint(moveEvent);
    renderPoints();
  };
  const up = () => {
    overlay.removeEventListener("pointermove", move);
    overlay.removeEventListener("pointerup", up);
  };
  overlay.addEventListener("pointermove", move);
  overlay.addEventListener("pointerup", up);
});

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) return;
  preview.src = URL.createObjectURL(file);
  editor.classList.toggle("hidden", !useBox.checked);
  renderPoints();
});

useBox.addEventListener("change", () => {
  editor.classList.toggle("hidden", !useBox.checked || !preview.src);
});

document.querySelector("#save-default").addEventListener("click", () => {
  localStorage.setItem(defaultKey, JSON.stringify(points));
  status.textContent = "Saved default box for this browser.";
});

document.querySelector("#clear-default").addEventListener("click", () => {
  localStorage.removeItem(defaultKey);
  status.textContent = "Cleared saved default box.";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = imageInput.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("raw_image", file);
  if (useBox.checked) {
    const box = points.map(([x, y]) => [x * preview.naturalWidth, y * preview.naturalHeight]);
    formData.append("bounding_box", JSON.stringify(box));
  }
  const collectionId = document.querySelector("#collection-id").value;
  const response = await fetch(`/collections/${collectionId}/unverified-cards`, {
    method: "POST",
    body: formData,
  });
  status.textContent = response.ok ? "Image registered." : `Registration failed (${response.status}).`;
});

renderPoints();
