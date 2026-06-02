document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("download-form");
    const submitBtn = document.getElementById("submit-btn");
    const btnText = document.getElementById("btn-text");
    const statusCard = document.getElementById("status-card");
    const statusMessage = document.getElementById("status-message");
    const progressBar = document.getElementById("progress-bar");
    const spinner = document.getElementById("status-spinner");

    let progressInterval = null;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const urlInput = document.getElementById("url").value.trim();
        const modeInput = document.querySelector('input[name="mode"]:checked').value;

        if (!urlInput) return;

        // UI Reset e exibição do progresso
        setLoadingState(true);
        startProgressSimulation();

        const formData = new FormData();
        formData.append("url", urlInput);
        formData.append("mode", modeInput);

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                // Tenta extrair a mensagem de erro detalhada do servidor
                let errorMsg = "O download falhou. Verifique o link e tente novamente.";
                try {
                    const errData = await response.json();
                    if (errData && errData.detail) {
                        errorMsg = errData.detail;
                    }
                } catch (e) {}
                throw new Error(errorMsg);
            }

            // Pega o nome do arquivo a partir do cabeçalho Content-Disposition
            let filename = modeInput === "audio" ? "audio.mp3" : "video.mp4";
            const contentDisposition = response.headers.get("Content-Disposition");
            if (contentDisposition) {
                const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, "");
                }
            }

            const blob = await response.blob();
            
            // Simulação finalizada com sucesso
            completeProgress();
            
            // Dispara o download nativo do navegador
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);

            showSuccess("Download concluído com sucesso!");

        } catch (error) {
            loggerError(error.message);
        } finally {
            setLoadingState(false);
        }
    });

    function setLoadingState(isLoading) {
        if (isLoading) {
            submitBtn.disabled = true;
            btnText.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Processando...';
            statusCard.classList.remove("hidden");
            statusCard.scrollIntoView({ behavior: 'smooth' });
        } else {
            submitBtn.disabled = false;
            btnText.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Iniciar Download';
        }
    }

    function startProgressSimulation() {
        if (progressInterval) clearInterval(progressInterval);
        
        spinner.className = "spinner"; // Reset classes
        spinner.innerHTML = ""; // Reset content (icons)
        progressBar.style.backgroundColor = ""; // Reset cor
        progressBar.style.width = "0%";
        
        let width = 0;
        statusMessage.textContent = "📥 Link enviado! Conectando à plataforma...";

        progressInterval = setInterval(() => {
            if (width < 30) {
                width += 5;
                statusMessage.textContent = "🔍 Analisando informações e links de mídia...";
            } else if (width < 60) {
                width += 2;
                statusMessage.textContent = "⚡ Baixando áudio e vídeo de alta qualidade...";
            } else if (width < 85) {
                width += 1;
                statusMessage.textContent = "🎬 Fundindo vídeo e áudio em formato universal MP4...";
            } else if (width < 95) {
                width += 0.2; // desacelera no final
                statusMessage.textContent = "📦 Finalizando conversão e preparando envio...";
            }
            progressBar.style.width = width + "%";
        }, 300);
    }

    function completeProgress() {
        if (progressInterval) clearInterval(progressInterval);
        progressBar.style.width = "100%";
    }

    function showSuccess(msg) {
        statusMessage.textContent = msg;
        spinner.className = "spinner success";
        spinner.innerHTML = '<i class="fa-solid fa-circle-check" style="color: var(--success-color); font-size: 18px;"></i>';
    }

    function loggerError(msg) {
        if (progressInterval) clearInterval(progressInterval);
        statusMessage.textContent = msg;
        progressBar.style.width = "100%";
        progressBar.style.backgroundColor = "var(--error-color)";
        spinner.className = "spinner error";
        spinner.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color: var(--error-color); font-size: 18px;"></i>';
    }
});
