const estoque = [];

function renderizarEstoque() {
  const tbody = document.getElementById("lista-estoque");
  tbody.innerHTML = "";

  estoque.forEach((item) => {
    const linha = document.createElement("tr");
    linha.innerHTML = `<td>${item.nome}</td><td>${item.quantidade}</td>`;
    tbody.appendChild(linha);
  });
}

function adicionarProduto() {
  const produto = document.getElementById("produto");
  const quantidade = document.getElementById("quantidade");

  const nome = produto.value.trim();
  const qtd = Number(quantidade.value);

  if (!nome || Number.isNaN(qtd)) {
    alert("Preencha o nome do produto e a quantidade.");
    return;
  }

  estoque.push({ nome, quantidade: qtd });
  produto.value = "";
  quantidade.value = "";
  renderizarEstoque();
}
