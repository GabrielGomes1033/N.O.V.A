function login() {
  const email = document.getElementById("email").value.trim();
  const senha = document.getElementById("senha").value.trim();
  const feedback = document.getElementById("feedback");

  if (!email || !senha) {
    feedback.textContent = "Preencha e-mail e senha para continuar.";
    return;
  }

  feedback.textContent = "Interface pronta. Agora conecte este login ao backend.";
}
