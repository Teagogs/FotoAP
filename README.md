# FotoFinder 📸

O **FotoFinder** é uma ferramenta avançada de organização de fotos baseada em Inteligência Artificial. Ele utiliza reconhecimento facial para agrupar pessoas automaticamente ou encontrar indivíduos específicos em grandes volumes de arquivos.

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
   git clone https://github.com/SEU_USUARIO/foto-finder-pro.git

2. Instale as dependências:
   pip install -r requirements.txt

3. Inicie o aplicativo::
   python app/main.py

   📂 Estrutura do Projeto

📁 app/
    📄 main.py           # Ponto de entrada (executável)
    📁 core/             # Lógica de processamento e IA
    📁 ui/               # Interface gráfica e gerenciamento de grid
    📁 workers/          # Funções para processamento em paralelo

📄 fotofinder_config.json # Configurações persistentes do usuário

⚙️ Configurações de Análise
    Preciso: Menor tolerância a erros, evita misturar pessoas parecidas.
    Abrangente: Maior tolerância, útil quando as fotos têm iluminação ruim ou ângulos variados.
    Downscale: O modo "Muito Rápido" reduz o tempo de análise em até 75% em fotos de alta resolução.

⚖️ Licença
Este projeto está sob a licença MIT.