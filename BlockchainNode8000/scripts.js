const API_URL = 'http://localhost:5000';

let currentUser = null;

// Dicionário de unidades e cursos
const unidadesCursos = {
    "Escola Normal Superior": [
        "Ciências Biológicas", "Geografia", "História", "Letras - Língua Portuguesa", "Matemática", "Pedagogia"
    ],
    "Escola Superior de Artes e Turismo": [
        "Dança", "Música - Canto", "Música - Regência", "Música - Instrumento", "Teatro", "Turismo"
    ],
    "Escola Superior de Ciências Sociais": [
        "Administração", "Arqueologia", "Ciências Contábeis", "Ciências Econômicas", "Direito", "Segurança Pública e do Cidadão"
    ],
    "Escola Superior de Ciências da Saúde": [
        "Enfermagem", "Farmácia", "Medicina", "Odontologia", "Saúde Coletiva"

    ],
    "Escola Superior de Tecnologia": [
        "Engenharia Civil", "Engenharia Eletrônica", "Engenharia Elétrica", "Engenharia Mecatrônica", "Engenhatia Mecânica",
        "Engenharia Naval", "Engenharia Química", "Engenharia de Computação", "Engenharia de Controle e Automação",
        "Engenharia de Materiais", "Engenharia de Produção", "Meteorologia", "Sistemas de Informação"
    ]
};

// Mostrar seção de criação de usuário
function showCreateUser() {
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('create-user-section').classList.remove('hidden');
}

// Mostrar seção de login
function showLogin() {
    document.getElementById('create-user-section').classList.add('hidden');
    document.getElementById('recharge-section').classList.add('hidden');
    document.getElementById('login-section').classList.remove('hidden');
}

// Mostrar seção de recarga
function showRecharge() {
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('create-user-section').classList.add('hidden');
    document.getElementById('recharge-section').classList.remove('hidden');
    document.getElementById('transaction-history').classList.remove('hidden');
}

// Função de validação principal
function validateInputs() {
    // Validação da matrícula (10 dígitos)
    const matricula = document.getElementById('new-matricula').value;
    if (matricula.length !== 10 || isNaN(matricula)) {
        showMessage('A matrícula deve ter exatamente 10 números', true);
        return false;
    }

    // Validação do código de segurança (4 dígitos)
    const cv = document.getElementById('new-cv').value;
    if (cv.length !== 4 || isNaN(cv)) {
        showMessage('O código de segurança deve ter exatamente 4 números', true);
        return false;
    }

    // Validação do nome (não vazio)
    const nome = document.getElementById('new-name').value;
    if (!nome.trim()) {
        showMessage('O nome completo é obrigatório', true);
        return false;
    }

    // Validação da unidade e curso
    const unidade = document.getElementById('unidade').value;
    const curso = document.getElementById('curso').value;
    if (!unidade || !curso) {
        showMessage('Selecione uma unidade e um curso válidos', true);
        return false;
    }

    // Validação do RG (pelo menos 5 dígitos)
    const rg = document.getElementById('new-rg').value;
    if (isNaN(rg)) {
        showMessage('O RG deve ser composto apenas por números', true);
        return false;
    }

    // Validação das datas
    const dataNascimento = document.getElementById('new-date-birth').value;
    const dataExpedicao = document.getElementById('new-date-exp').value;

    if (dataNascimento && dataExpedicao) {
        const nascimento = new Date(dataNascimento);
        const expedicao = new Date(dataExpedicao);

        if (expedicao < nascimento) {
            showMessage('A data de expedição não pode ser anterior à data de nascimento', true);
            return false;
        }

        // Valida se a data de expedição não é no futuro
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0); // Remove a parte de horas para comparar apenas datas

        if (expedicao > hoje) {
            showMessage('A data de expedição não pode ser no futuro', true);
            return false;
        }
    } else if (!dataNascimento && dataExpedicao) {
        showMessage('Preencha a data de nascimento para validar a data de expedição', true);
        return false;
    }

    return true;
}

// Função createUser atualizada
async function createUser() {
    if (!validateInputs()) {
        return;
    }

    const matricula = document.getElementById('new-matricula').value;
    const cv = document.getElementById('new-cv').value;
    const nome = document.getElementById('new-name').value;
    const unidade = document.getElementById('unidade').value;
    const curso = document.getElementById('curso').value;
    const rg = document.getElementById('new-rg').value;
    const dataExpedicao = document.getElementById('new-date-exp').value;
    const dataNascimento = document.getElementById('new-date-birth').value;

    try {
        await axios.post(`${API_URL}/createUser`, {
            matricula: parseInt(matricula),
            cv,
            nome,
            curso,
            unidade,
            rg,
            dataExpedicao,
            dataNascimento
        });

        let balance = 0;

        await axios.get(`${API_URL}/balance/${matricula}`)
            .then(response => {
                balance = response.data.balance;
            })
            .catch(error => {
                console.error('Erro ao obter saldo:', error);
            });

        currentUser = matricula;
        updateUserInfo(matricula, nome, rg, unidade, curso, balance);
        showRecharge();
        await updateBalance();
        showMessage('Carteirinha criada com sucesso!');
    } catch (error) {
        showMessage(error.response?.data?.error || 'Erro ao criar carteirinha', true);
    }
}

// Validação no login
async function getUser() {
    const matricula = document.getElementById('matricula').value;

    if (matricula.length !== 10) {
        showMessage('A matrícula deve ter exatamente 10 dígitos', true);
        return;
    }

    try {
        let balance = 0;

        await axios.get(`${API_URL}/balance/${matricula}`)
            .then(response => {
                balance = response.data.balance;
            })
            .catch(error => {
                console.error('Erro ao obter saldo:', error);
            });

        await axios.get(`${API_URL}/student/${matricula}`).
            then(response => {
                const { nome, rg, unidade, curso } = response.data;
                updateUserInfo(matricula, nome, rg, unidade, curso, balance);
            })
            .catch(error => {
                showMessage('Matrícula não encontrada', true);
                return;
            });

        currentUser = matricula;
        showRecharge();
        await updateBalance();
    } catch (error) {
        showMessage('Matrícula não encontrada', true);
        return;
    }
}

// Validação na recarga
async function recharge() {
    const amount = parseFloat(document.getElementById('recharge-amount').value);

    if (!amount || amount <= 0) {
        showMessage('Digite um valor válido (maior que zero)', true);
        return;
    }

    try {
        const keysResponse = await axios.get(`${API_URL}/generate_keys`);

        const txData = {
            student_id: parseInt(currentUser),
            amount
        };
        console.log("txData para assinar:", txData);

        const signResponse = await axios.post(`${API_URL}/sign`, {
            tx_data: JSON.stringify(txData, Object.keys(txData).sort()),
            private_key: keysResponse.data.private_key,
        });

        await axios.post(`${API_URL}/recharge`, {
            ...txData,
            signature: signResponse.data.signature,
            public_key: keysResponse.data.public_key
        });

        await updateBalance();
        showMessage('Recarga realizada com sucesso!');
        document.getElementById('recharge-amount').value = '';
    } catch (error) {
        showMessage(error.response?.data?.detail || 'Erro na recarga', true);
    }
}

// Exibir mensagem temporária
function showMessage(text, isError = false) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = isError ? 'error' : 'success';
    msg.classList.remove('hidden');

    setTimeout(() => {
        msg.classList.add('hidden');
    }, 3000);
}

// Atualizar informações do usuário no cabeçalho
function updateUserInfo(matricula, name, rg, unidade, curso, balance) {
    document.getElementById('current-matricula').textContent = matricula;
    document.getElementById('current-name').textContent = name;
    document.getElementById('current-rg').textContent = rg;
    document.getElementById('current-uni').textContent = unidade;
    document.getElementById('current-crs').textContent = curso;
    document.getElementById('current-balance').textContent = balance.toFixed(2);
    document.getElementById('user-info').classList.remove('hidden');
}

// Atualizar saldo
async function updateBalance() {
    if (!currentUser) return;

    try {
        const response = await axios.get(`${API_URL}/balance/${currentUser}`);
        document.getElementById('current-balance').textContent =
            response.data.balance.toFixed(2);
    } catch (error) {
        console.error('Erro ao atualizar saldo:', error);
    }
}

// Inicializa os selects quando a página carrega
document.addEventListener('DOMContentLoaded', () => {
    const unidadeSelect = document.getElementById('unidade');

    // Preenche o select de unidades
    for (const unidade in unidadesCursos) {
        const option = document.createElement('option');
        option.value = unidade;
        option.textContent = unidade;
        unidadeSelect.appendChild(option);
    }
});

// Atualiza os cursos quando uma unidade é selecionada
function updateCursos() {
    const unidadeSelect = document.getElementById('unidade');
    const cursoSelect = document.getElementById('curso');
    const unidadeSelecionada = unidadeSelect.value;

    // Limpa e desabilita o select de cursos
    cursoSelect.innerHTML = '';
    cursoSelect.disabled = !unidadeSelecionada;

    if (unidadeSelecionada) {
        // Adiciona a opção padrão
        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "Selecione seu Curso";
        cursoSelect.appendChild(defaultOption);

        // Preenche com os cursos da unidade selecionada
        unidadesCursos[unidadeSelecionada].forEach(curso => {
            const option = document.createElement('option');
            option.value = curso;
            option.textContent = curso;
            cursoSelect.appendChild(option);
        });

        cursoSelect.disabled = false;
    }
}

// Variável global para controlar o estado do histórico
let isHistoryOpen = false;

// Adicione esta função para alternar a visibilidade do histórico
function toggleHistory() {
    isHistoryOpen = !isHistoryOpen;
    const content = document.getElementById('history-content');
    const arrow = document.getElementById('history-arrow');
    
    if (isHistoryOpen) {
        content.classList.remove('hidden');
        arrow.textContent = '▲';
        fetchStudentData(currentUser); // Atualiza o histórico ao abrir
    } else {
        content.classList.add('hidden');
        arrow.textContent = '▼';
    }
}

// Modifique a função fetchStudentData para garantir que o histórico aparece
async function fetchStudentData(matricula) {
    try {
        const [alunoResponse, balanceResponse, historyResponse] = await Promise.all([
            axios.get(`${API_URL}/student/${matricula}`),
            axios.get(`${API_URL}/balance/${matricula}`),
            axios.get(`${API_URL}/transaction_history/${matricula}`)
        ]);

        // Atualiza informações básicas
        document.getElementById('current-matricula').textContent = matricula;
        document.getElementById('current-name').textContent = alunoResponse.data.nome || 'Não informado';
        document.getElementById('current-balance').textContent = balanceResponse.data.balance?.toFixed(2) || '0.00';
        
        // Mostra seção do usuário
        const userInfoDiv = document.getElementById('user-info');
        userInfoDiv.classList.remove('hidden');
        
        // Atualiza e mostra histórico de transações
        updateTransactionHistory(historyResponse.data);
        document.getElementById('transaction-history').classList.remove('hidden'); // Garante que está visível
        
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
        showMessage('Erro ao carregar dados. Tente novamente.', true);
    }
}

// Adicione esta função para resetar a interface corretamente
function resetInterface() {
    document.getElementById('transaction-history').classList.add('hidden');
    isHistoryOpen = false;
    document.getElementById('history-arrow').textContent = '▼';
    document.getElementById('transaction-history').classList.add('hidden');
}

// Função para atualizar o histórico de transações
function updateTransactionHistory(historyData) {
    const transactionsList = document.getElementById('transactions-list');
    
    // Limpa a lista atual
    transactionsList.innerHTML = '';
    
    // Adiciona cada transação à lista
    historyData.transactions.forEach(transaction => {
        const transactionItem = document.createElement('div');
        transactionItem.className = 'transaction-item';
        
        const isPositive = transaction.type === 'recarga';
        const symbol = isPositive ? '+' : '-';
        
        transactionItem.innerHTML = `
            <div>
            <span class="transaction-type">${transaction.type === 'pagamento' ? 'Compra de Ficha' : transaction.type}</span>
            <span class="transaction-date">${transaction.timestamp}</span>
            </div>
            <span class="transaction-amount ${isPositive ? 'positive' : 'negative'}">
            ${symbol} R$ ${transaction.amount.toFixed(2)}
            </span>
        `;
        
        transactionsList.appendChild(transactionItem);
    });
}