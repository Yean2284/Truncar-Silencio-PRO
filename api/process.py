const processAudio = async () => {
    if (!file) return;
    setIsProc(true);
    setProg(5);
    
    try {
        // URL de tu API en Vercel (cambiar después del deploy)
        const API_URL = window.location.origin + '/api/process';
        
        // Crear FormData con el archivo
        const formData = new FormData();
        formData.append('audio', file);
        
        setProg(15);
        
        // Enviar al servidor
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData,
        });
        
        setProg(40);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.details || errorData.error || 'Error en el servidor');
        }
        
        setProg(70);
        
        // Recibir archivo procesado
        const blob = await response.blob();
        setProg(95);
        
        const finalSize = (blob.size / 1024 / 1024).toFixed(2);
        console.log(`✅ MP3 generado: ${finalSize}MB`);
        
        setUrl(URL.createObjectURL(blob));
        setProg(100);
        
        showInterstitial();
        
    } catch (e) { 
        console.error('❌ Error procesando audio:', e);
        
        let errorMsg = '⚠️ Error al procesar el audio.';
        
        if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
            errorMsg = '⚠️ Error de conexión.\n\nVerifica tu internet e intenta de nuevo.';
        } else if (e.message.includes('grande')) {
            errorMsg = '⚠️ Archivo demasiado grande.\n\nMáximo permitido: 200MB';
        } else if (e.message.includes('silencio')) {
            errorMsg = '⚠️ El archivo solo contiene silencio.\n\nIntenta con otro archivo.';
        } else {
            errorMsg = `⚠️ Error: ${e.message}\n\nIntenta de nuevo o con otro archivo.`;
        }
        
        alert(errorMsg); 
        setProg(0);
    }
    
    setIsProc(false);
};
