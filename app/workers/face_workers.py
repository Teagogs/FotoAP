from PIL import Image
import numpy as np

try:
    import face_recognition
except ImportError:
    print("Erro: Bibliotecas de reconhecimento facial não encontradas. Instale com 'pip install face_recognition'.")
    exit()

def processar_imagem_cluster_worker(args):
    """
    Worker para extrair codificações de rosto de uma imagem para o processo de clusterização.
    Projetado para ser executado em um processo separado (multiprocessing).
    """
    caminho_imagem, downscale_factor = args
    try:
        if downscale_factor < 1.0:
            img = Image.open(caminho_imagem).convert("RGB")
            new_size = (int(img.width * downscale_factor), int(img.height * downscale_factor))
            img.thumbnail(new_size, Image.Resampling.LANCZOS)
            image_to_process = np.array(img)
        else:
            image_to_process = face_recognition.load_image_file(caminho_imagem)
        
        encodings = face_recognition.face_encodings(image_to_process)
        if encodings:
            return (caminho_imagem, encodings)
    except Exception:
        # Ignora erros em arquivos de imagem corrompidos ou não suportados
        pass
    return None

def processar_imagem_busca_worker(caminho_imagem, known_encodings, tolerance, downscale_factor):
    """
    Worker para comparar rostos em uma imagem com um conjunto de codificações conhecidas.
    Projetado para ser executado em um processo separado (multiprocessing).
    """
    try:
        if downscale_factor < 1.0:
            img = Image.open(caminho_imagem).convert("RGB")
            new_size = (int(img.width * downscale_factor), int(img.height * downscale_factor))
            img.thumbnail(new_size, Image.Resampling.LANCZOS)
            image_to_process = np.array(img)
        else:
            image_to_process = face_recognition.load_image_file(caminho_imagem)
            
        unknown_encodings = face_recognition.face_encodings(image_to_process)
        
        for unknown_encoding in unknown_encodings:
            for person_name, ref_encoding in known_encodings.items():
                if face_recognition.compare_faces([ref_encoding], unknown_encoding, tolerance=tolerance)[0]:
                    return (caminho_imagem, person_name)
    except Exception:
        pass
    return None