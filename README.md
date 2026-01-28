# FotoFinder Pro 📸

O **FotoFinder Pro** é uma ferramenta avançada de organização de fotos baseada em Inteligência Artificial. Ele utiliza reconhecimento facial para agrupar pessoas automaticamente ou encontrar indivíduos específicos em grandes volumes de arquivos.

## ✨ Funcionalidades

- **Agrupamento Automático (Clustering):** Analisa uma pasta inteira e separa cada pessoa encontrada em pastas exclusivas (`Pessoa_01`, `Pessoa_02`, etc.) usando o algoritmo DBSCAN.
- **Busca Individual:** Localize todas as fotos de uma pessoa específica fornecendo apenas uma foto de referência.
- **Busca em Lote:** Use uma pasta de "rostos conhecidos" para organizar automaticamente uma biblioteca inteira de fotos.
- **Processamento Paralelo:** Utiliza múltiplos núcleos do seu processador (Multiprocessing) para acelerar a análise de milhares de fotos.
- **Otimização de Velocidade:** Opções de *Downscale* para processar imagens em resoluções menores, mantendo a precisão.
- **Interface Moderna:** UI desenvolvida com `customtkinter` com suporte a Dark Mode e visualização de resultados em tempo real.

## 🛠️ Tecnologias

- **Python 3.10+**
- **face_recognition (dlib):** Reconhecimento de pontos faciais e codificação.
- **Scikit-learn:** Agrupamento espacial (DBSCAN) para identificar padrões de rostos.
- **CustomTkinter:** Interface gráfica moderna e responsiva.
- **Pillow:** Manipulação e otimização de miniaturas.

## 🚀 Como Executar

### Pré-requisitos
Devido à biblioteca `face_recognition`, você precisará do **CMake** e do **C++ Compiler** instalados no seu sistema (via Visual Studio Build Tools no Windows).

1. Clone o repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/foto-finder-pro.git