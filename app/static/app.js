let sessionId = null;
let currentBlock = null;
let completedBlocks = 0;
let pendingNextBlock = null;

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

function setSessionMeta() {
  document.getElementById("session-id").textContent = sessionId || "-";
  document.getElementById("current-topic").textContent = currentBlock?.topic_id || "-";
  document.getElementById("progress-counter").textContent = `${completedBlocks} blocos`;
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
  return {
    ...block,
    type: "questions",
  };
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
      <h3>${block.topic_id}</h3>
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
      <h3>${block.topic_id}</h3>
      <p class="block-content">${block.statement}</p>
      <div class="actions-row">
        <button id="answer-true">Certo</button>
        <button id="answer-false" class="danger-button">Errado</button>
      </div>
    </article>
  `;

  document.getElementById("answer-true").addEventListener("click", () => submitQuestionAnswer(true));
  document.getElementById("answer-false").addEventListener("click", () => submitQuestionAnswer(false));
}

function renderFeedback(isCorrect, explanation, nextBlock) {
  const statusClass = isCorrect ? "success-text" : "danger-text";
  const statusText = isCorrect ? "Correto" : "Errado";
  pendingNextBlock = nextBlock || null;

  document.getElementById("content-area").innerHTML = `
    <article class="feedback-card">
      <span class="${statusClass}">${statusText}</span>
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
  setSessionMeta();
  document.getElementById("content-area").innerHTML = `
    <article class="block-card">
      <span class="block-type">Concluído</span>
      <h3>Sessão concluída</h3>
      <p class="block-content">Você terminou todos os blocos desta sessão.</p>
      <button id="restart-button">Nova sessão</button>
    </article>
  `;

  document.getElementById("restart-button").addEventListener("click", startSession);
}

async function startSession() {
  try {
    completedBlocks = 0;
    pendingNextBlock = null;
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
    renderPlaceholder(error.message);
  }
}

async function advanceSummaryBlock() {
  if (!sessionId) {
    return;
  }

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
    alert(error.message);
  }
}

function askErrorType() {
  const value = window.prompt(
    "Informe o tipo de erro: conceptual, interpretation, memory ou attention",
    "conceptual"
  );
  if (!value) {
    return null;
  }
  return value.trim().toLowerCase();
}

async function submitQuestionAnswer(userAnswer) {
  if (!sessionId || !currentBlock) {
    return;
  }

  const isCorrect = userAnswer === currentBlock.correct_answer;
  let errorType = null;

  if (!isCorrect) {
    errorType = askErrorType();
    if (!errorType) {
      alert("É necessário informar o tipo de erro.");
      return;
    }
  }

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

    if (payload.completed) {
      renderFeedback(payload.correct, currentBlock.explanation, null);
      return;
    }

    renderFeedback(payload.correct, currentBlock.explanation, payload.next_block);
  } catch (error) {
    alert(error.message);
  }
}

document.getElementById("start-session-button").addEventListener("click", startSession);
setSessionMeta();
