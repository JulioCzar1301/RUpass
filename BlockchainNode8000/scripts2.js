const API_URL = 'http://localhost:5000';
let stream = null;
let scanInterval = null;
let currentMatricula = null;
let currentCodigoSeguranca = null;

// Elementos da interface
const startCameraBtn = document.getElementById('start-camera');
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const cameraContainer = document.getElementById('camera-container');
const userInfoDiv = document.getElementById('user-info');
const scanSection = document.getElementById('scan-section');
const ticketSection = document.getElementById('ticket-section');
const confirmSection = document.getElementById('confirm-section');
const selectedTicketSpan = document.getElementById('selected-ticket');
const selectedPriceSpan = document.getElementById('selected-price');

// Iniciar câmera e escanear automaticamente
startCameraBtn.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
        });
        video.srcObject = stream;
        cameraContainer.classList.remove('hidden');
        startCameraBtn.classList.add('hidden');
        showMessage('Aproxime a carteirinha do código de barras da câmera');

        scanInterval = setInterval(scanBarcode, 1000);
    } catch (err) {
        console.error('Erro ao acessar câmera:', err);
        showMessage('Erro ao acessar a câmera: ' + err.message, true);
    }
});

// Escanear código de barras
async function scanBarcode() {
    if (!stream) return;

    try {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const imageData = canvas.toDataURL('image/jpeg');
        const response = await axios.post(`${API_URL}/scan`, { image: imageData });

        if (response.data.status === 'success' && response.data.data.length === 14) {
            clearInterval(scanInterval);
            stopCamera();

            currentMatricula = response.data.data.substring(0, 10);
            currentCodigoSeguranca = response.data.data.substring(10, 14);

            await fetchStudentData(parseInt(currentMatricula));
            showTicketOptions();
        }

    } catch (error) {
        console.error('Erro durante o scan:', error);
    }
}

// Mostrar opções de fichas
function showTicketOptions() {
    scanSection.classList.add('hidden');
    ticketSection.classList.remove('hidden');
    updateTicketAvailability();
}

// Atualizar disponibilidade das fichas conforme horário
function updateTicketAvailability() {
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinutes = now.getMinutes();
    const tickets = document.querySelectorAll('.ticket-card');

    tickets.forEach(ticket => {
        const type = ticket.dataset.type;
        let isAvailable = false;

        switch (type) {
            case 'cafe':
                isAvailable = (currentHour > 6 || (currentHour === 6 && currentMinutes >= 30)) && currentHour <= 9;
                break;
            case 'almoco':
                isAvailable = (currentHour > 11 || (currentHour === 11 && currentMinutes >= 30)) && currentHour <= 14;
                break;
            case 'lanche':
                isAvailable = (currentHour > 17 || (currentHour === 17 && currentMinutes >= 30))
                    && (currentHour < 19 || (currentHour === 19 && currentMinutes <= 30));
                break;
            case 'janta':
                isAvailable = currentHour >= 18 && currentHour <= 20;
                break;
        }

        ticket.classList.toggle('disabled', !isAvailable);
        ticket.querySelector('.select-btn').disabled = !isAvailable;
    });
}

// Selecionar ficha
document.querySelectorAll('.select-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        const ticketCard = this.closest('.ticket-card');
        const ticketType = ticketCard.dataset.type;
        const ticketPrice = ticketCard.dataset.price;

        selectedTicketSpan.textContent = this.parentNode.querySelector('h3').textContent;
        selectedPriceSpan.textContent = ticketPrice;

        ticketSection.querySelector('h2').textContent = 'Confirmar Compra';
        confirmSection.classList.remove('hidden');
    });
});

// Cancelar compra
document.getElementById('cancel-purchase').addEventListener('click', () => {
    confirmSection.classList.add('hidden');
    ticketSection.querySelector('h2').textContent = 'Selecione a Ficha';
});

// Confirmar compra
document.getElementById('confirm-purchase').addEventListener('click', async () => {
    try {
        const ticketType = selectedTicketSpan.textContent;
        const ticketPrice = parseFloat(selectedPriceSpan.textContent);

        const balanceResponse = await axios.get(`${API_URL}/balance/${currentMatricula}`);

        if (balanceResponse.data.balance >= ticketPrice) {

            const keysResponse = await axios.get(`${API_URL}/generate_keys`);

            const txData = {
                student_id: parseInt(currentMatricula),
                codigo_seguranca: currentCodigoSeguranca,
                amount: ticketPrice
            };

            const signResponse = await axios.post(`${API_URL}/sign`, {
                tx_data: JSON.stringify(txData, Object.keys(txData).sort()),
                private_key: keysResponse.data.private_key,
            });


            const response = await axios.post(`${API_URL}/payment`, {
                ...txData,
                signature: signResponse.data.signature,
                public_key: keysResponse.data.public_key
            });

            showMessage('Compra realizada com sucesso!');
            await fetchStudentData(currentMatricula);

            // Gerar nota fiscal
            const alunoNome = document.getElementById('current-name').textContent;
            generateInvoice(alunoNome, currentMatricula, ticketType, ticketPrice);

            resetInterface();
        } else {
            showMessage('Saldo insuficiente para realizar a compra', true);
            confirmSection.classList.add('hidden');
        }

    } catch (error) {
        console.error('Erro na compra:', error);
        showMessage(error.response?.data?.detail || 'Erro ao realizar compra', true);
    }
});

// Função para gerar nota fiscal em PDF
function generateInvoice(alunoNome, matricula, ticketType, price) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Configurações do PDF
    const date = new Date().toLocaleString('pt-BR');
    const timestamp = Date.now();
    const invoiceNumber = 'NF-' + timestamp;

    // Cabeçalho
    doc.setFontSize(18);
    doc.setTextColor(40);
    doc.setFont(undefined, 'bold');
    doc.text('NOTA FISCAL ELETRÔNICA', 105, 20, { align: 'center' });
    doc.setFont(undefined, 'normal');

    doc.setFontSize(12);
    doc.text(`Número: ${invoiceNumber}`, 14, 30);
    doc.text(`Data: ${date}`, 14, 37);

    // Informações do Aluno
    doc.setFontSize(14);
    doc.setFont(undefined, 'bold');
    doc.text('DADOS DO ALUNO', 14, 50);
    doc.setFont(undefined, 'normal');

    doc.setFontSize(12);
    doc.text(`Nome: ${alunoNome}`, 14, 60);
    doc.text(`Matrícula: ${matricula}`, 14, 67);

    // Detalhes da Compra
    doc.setFontSize(14);
    doc.setFont(undefined, 'bold');
    doc.text('DETALHES DA COMPRA', 14, 80);
    doc.setFont(undefined, 'normal');

    // Tabela de itens
    doc.autoTable({
        startY: 85,
        head: [['Descrição', 'Valor']],
        body: [
            ["FICHA (" + ticketType + ")", `R$ ${price.toFixed(2)}`]
        ],
        theme: 'grid',
        headStyles: {
            fillColor: [27, 165, 80],
            textColor: 255
        },
        styles: {
            cellPadding: 3,
            fontSize: 10,
            valign: 'middle'
        },
        columnStyles: {
            0: { cellWidth: 'auto' },
            1: { cellWidth: 'auto' }
        }
    });

    // Rodapé
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text('Sistema PassaRU - Universidade Federal do Estado do Amazonas', 105, 285, { align: 'center' });

    // Salvar o PDF
    doc.save(`NotaFiscal-${invoiceNumber}.pdf`);
}

// Buscar dados do aluno
async function fetchStudentData(matricula) {
    try {
        const [alunoResponse, balanceResponse] = await Promise.all([
            axios.get(`${API_URL}/student/${matricula}`),
            axios.get(`${API_URL}/balance/${matricula}`)
        ]);

        document.getElementById('current-matricula').textContent = matricula;
        document.getElementById('current-name').textContent = alunoResponse.data.nome || 'Não informado';
        document.getElementById('current-balance').textContent = balanceResponse.data.balance?.toFixed(2) || '0.00';
        userInfoDiv.classList.remove('hidden');
    } catch (error) {
        console.error('Erro ao buscar aluno:', error);
        showMessage('Erro ao buscar dados do aluno', true);
    }
}

// Resetar interface
function resetInterface() {
    ticketSection.classList.add('hidden');
    confirmSection.classList.add('hidden');
    scanSection.classList.remove('hidden');
    startCameraBtn.classList.remove('hidden');
    ticketSection.querySelector('h2').textContent = 'Selecione a Ficha';
}

// Parar câmera
function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    cameraContainer.classList.add('hidden');
}

// Mostrar mensagens
function showMessage(text, isError = false) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.className = isError ? 'error' : 'success';
    msg.classList.remove('hidden');

    setTimeout(() => {
        msg.classList.add('hidden');
    }, 3000);
}

// Gerenciar recursos ao sair
window.addEventListener('beforeunload', () => {
    if (stream) stopCamera();
    if (scanInterval) clearInterval(scanInterval);
});