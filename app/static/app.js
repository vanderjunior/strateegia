let sessionId = null;
let currentBlock = null;
let pendingNextBlock = null;
let completedBlocks = 0;
let totalBlocks = null;
let correctCount = 0;
let incorrectCount = 0;
let isLoading = false;

const ERROR_TYPES = [
  { key: "conceptual", label: "Conceptual" },
  { key: "interpretation", label: "Interpretation" },
  { key: "memory", label: "Memory" },
  { key: "attention", label: "Attention" },
];

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Erro inesperado." }));
    throw new Error(payload.detail || "Erro inesperado.");
  }

  return response.json();
}

function humanizeTopic(topicId) {
  if (!topicId) {
    return "-";
  }
  return topicId
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function currentBlockNumber() {
  return currentBlock ? completedBlocks + 1 : completedBlocks;
}

function totalBlocksLabel() {
  return totalBlocks ?? "?";
}

function setLoadingState(nextState, label = "Loading...") {
  isLoading = nextState;
  const indicator = document.getElementById("loading-indicator");
  indicator.textContent = label;
  indicator.classList.toggle("hidden", !nextState);

  document.querySelectorAll("button").forEach((button) => {
    button.disabled = nextState;
  });
}

function showErrorBanner(message = "Erro ao comunicar com o servidor. Tente novamente.") {
  const banner = document.getElementById("error-banner");
  banner.textContent = message;
  banner.classList.remove("hidden");
}

function hideErrorBanner() {
  document.getElementById("error-banner").classList.add("hidden");
}

function setSessionMeta() {
  const topicName = currentBlock ? humanizeTopic(currentBlock.topic_id) : "-";
  const progressText = `Bloco ${currentBlockNumber()} de ${totalBlocksLabel()}`;

  document.getElementById("session-id").textContent = sessionId || "-";
  document.getElementById("current-topic").textContent = topicName;
  document.getElementById("progress-counter").textContent = progressText;
  document.getElementById("answer-stats").textContent = `${correctCount} corretas · ${incorrectCount} incorretas`;
  document.getElementById("block-progress").textContent = `${progressText} — Tópico: ${topicName}`;
  document.getElementById("session-status").textContent = sessionId
    ? currentBlock
      ? "Em andamento"
      : "Sessão concluída"
    : "Aguardando início";
}

function renderPlaceholder(message) {
  document.getElementById("content-area").innerHTML = `<div class="placeholder">${message}</div>`;
}

function normalizeQuestionBlock(block) {
  if (!block || block.type !== "question") {
    return block;
  }
  return { ...block, type: "questions" };
}

function renderBlock(block) {
  currentBlock = normalizeQuestionBlock(block);
  setSessionMeta();

  if (!currentBlock) {
    renderCompletion();
    return;
  }

  if (currentBlock.type === "summary") {
    renderSummaryBlock(currentBlock);
    return;
  }

  if (currentBlock.type === "questions") {
    renderQuestionBlock(currentBlock);
  }
}

function renderSummaryBlock(block) {
  document.getElementById("content-area").innerHTML = `
    <article class="block-card">
      <span class="block-type">Resumo</span>
      <h3>Tópico: ${humanizeTopic(block.topic_id)}</h3>
      <p class="block-content">${block.content}</p>
      <button id="continue-button" class="secondary-button">Continuar</button>
    </article>
  `;

  document.getElementById("continue-button").addEventListener("click", advanceSummaryBlock);
}

function renderQuestionBlock(block) {
  document.getElementById("content-area").innerHTML = `
    <article class="block-card">
      <span class="block-type">Questão</span>
      <h3>Tópico: ${humanizeTopic(block.topic_id)}</h3>
      <p class="block-content">${block.statement}</p>
      <div class="actions-row">
        <button id="answer-true">Certo</button>
        <button id="answer-false" class="danger-button">Errado</button>
      </div>
    </article>
  `;

  document.getElementById("answer-true").addEventListener("click", () => handleQuestionChoice(true));
  document.getElementById("answer-false").addEventListener("click", () => handleQuestionChoice(false));
}

function renderErrorTypeSelector(userAnswer) {
  document.getElementById("content-area").innerHTML = `
    <article class="block-card">
      <span class="block-type">Classificar erro</span>
      <h3>Tópico: ${humanizeTopic(currentBlock.topic_id)}</h3>
      <p class="block-content">Selecione o tipo de erro para continuar.</p>
      <div class="error-type-grid">
        ${ERROR_TYPES.map(
          (item) => `<button class="secondary-button error-type-button" data-error-type="${item.key}">${item.label}</button>`
        ).join("")}
      </div>
    </article>
  `;

  document.querySelectorAll(".error-type-button").forEach((button) => {
    button.addEventListener("click", () => {
      submitQuestionAnswer(userAnswer, button.dataset.errorType);
    });
  });
}

function renderFeedback(isCorrect, explanation, nextBlock) {
  pendingNextBlock = nextBlock || null;
  const statusText = isCorrect ? "Correto" : "Incorreto";
  const statusClass = isCorrect ? "feedback-success" : "feedback-error";

  document.getElementById("content-area").innerHTML = `
    <article class="feedback-card ${statusClass}">
      <span class="feedback-status">${statusText}</span>
      <p class="block-content">${explanation || "Resposta registrada."}</p>
      <button id="next-button" class="secondary-button">Próxima</button>
    </article>
  `;

  document.getElementById("next-button").addEventListener("click", () => {
    completedBlocks += 1;
    renderBlock(pendingNextBlock);
  });
}

function renderCompletion() {
  currentBlock = null;
  totalBlocks = completedBlocks;
  setSessionMeta();
  document.getElementById("content-area").innerHTML = `
    <article class="completion-card">
      <span class="block-type">Concluído</span>
      <h3>Sessão concluída</h3>
      <p class="block-content">Você terminou todos os blocos desta sessão.</p>
      <div class="session-stats">
        <span>${correctCount} corretas</span>
        <span>${incorrectCount} incorretas</span>
      </div>
      <button id="restart-button">Nova sessão</button>
    </article>
  `;

  document.getElementById("restart-button").addEventListener("click", startSession);
}

async function startSession() {
  hideErrorBanner();
  setLoadingState(true);

  try {
    sessionId = null;
    currentBlock = null;
    pendingNextBlock = null;
    completedBlocks = 0;
    totalBlocks = null;
    correctCount = 0;
    incorrectCount = 0;
    setSessionMeta();

    const payload = await fetchJson("/api/session/start", {
      method: "POST",
      body: JSON.stringify({ title: "Sessão de estudo", max_questions: 5 }),
    });

    sessionId = payload.session_id;

    if (!payload.first_block) {
      renderCompletion();
      return;
    }

    renderBlock(payload.first_block);
  } catch (error) {
    showErrorBanner();
    renderPlaceholder("Erro ao comunicar com o servidor. Tente novamente.");
  } finally {
    setLoadingState(false);
  }
}

async function advanceSummaryBlock() {
  if (!sessionId || isLoading) {
    return;
  }

  hideErrorBanner();
  setLoadingState(true);

  try {
    const payload = await fetchJson(`/api/session/${sessionId}/answer`, {
      method: "POST",
    });

    completedBlocks += 1;

    if (payload.completed || !payload.next_block) {
      renderCompletion();
      return;
    }

    renderBlock(payload.next_block);
  } catch (error) {
    showErrorBanner();
  } finally {
    setLoadingState(false);
  }
}

function handleQuestionChoice(userAnswer) {
  if (!currentBlock || isLoading) {
    return;
  }

  const isCorrect = userAnswer === currentBlock.correct_answer;
  if (!isCorrect) {
    renderErrorTypeSelector(userAnswer);
    return;
  }

  submitQuestionAnswer(userAnswer, null);
}

async function submitQuestionAnswer(userAnswer, errorType) {
  if (!sessionId || !currentBlock || isLoading) {
    return;
  }

  hideErrorBanner();
  setLoadingState(true);

  try {
    const payload = await fetchJson(`/api/session/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({
        question_id: currentBlock.question_id,
        user_answer: userAnswer,
        correct_answer: currentBlock.correct_answer,
        error_type: errorType,
      }),
    });

    if (payload.correct) {
      correctCount += 1;
    } else {
      incorrectCount += 1;
    }
    setSessionMeta();

    if (payload.completed) {
      renderFeedback(payload.correct, currentBlock.explanation, null);
      return;
    }

    renderFeedback(payload.correct, currentBlock.explanation, payload.next_block);
  } catch (error) {
    showErrorBanner();
    if (currentBlock.type === "questions") {
      renderQuestionBlock(currentBlock);
    }
  } finally {
    setLoadingState(false);
  }
}

document.getElementById("start-session-button").addEventListener("click", startSession);
setSessionMeta();
