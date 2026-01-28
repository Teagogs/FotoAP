# app/core/processing.py

import os
import shutil
import numpy as np
import functools
from multiprocessing import Pool, cpu_count

try:
    import face_recognition
    from sklearn.cluster import DBSCAN
except ImportError:
    print("Erro: Bibliotecas de processamento não encontradas. Instale com 'pip install face_recognition scikit-learn'.")
    exit()
    
from ..workers.face_workers import processar_imagem_cluster_worker, processar_imagem_busca_worker

class ProcessingEngine:
    """
    Contém a lógica de negócio principal para análise e agrupamento de fotos.
    Opera de forma desacoplada da UI, recebendo uma instância da janela principal
    para enviar atualizações de progresso.
    """
    def __init__(self, app_instance):
        self.app = app_instance

    def executar_busca_cluster(self):
        mapeamento_eps = {"Preciso": 0.45, "Equilibrado": 0.5, "Abrangente": 0.6}
        eps = mapeamento_eps[self.app.seg_button_precisao.get()]
        try:
            min_fotos_por_grupo = int(self.app.min_fotos_var.get())
            if min_fotos_por_grupo < 1: min_fotos_por_grupo = 2
        except (ValueError, TypeError):
            min_fotos_por_grupo = 2
        
        downscale_factor = self.app.get_downscale_factor()
        
        self.app.after(0, self.app.atualizar_status, "Passo 1/4: Mapeando arquivos...", 0)
        caminhos_imagens = [os.path.join(self.app.caminho_pasta_fotos, f) for f in os.listdir(self.app.caminho_pasta_fotos) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not caminhos_imagens:
            self.app.after(0, self.app.finalizar_busca, "Nenhuma imagem encontrada.")
            return

        self.app.after(0, self.app.atualizar_status, f"Passo 2/4: Processando {len(caminhos_imagens)} imagens...", 0.1)
        num_processos = max(1, cpu_count() - 1)
        args_para_worker = [(path, downscale_factor) for path in caminhos_imagens]
        
        all_encodings, encoding_to_path = [], {}
        total_imagens = len(caminhos_imagens)
        
        with Pool(processes=num_processos) as pool:
            resultados = pool.imap_unordered(processar_imagem_cluster_worker, args_para_worker)
            for i, res in enumerate(resultados):
                if self.app.stop_event.is_set():
                    pool.terminate()
                    self.app.after(0, self.app.finalizar_busca, "Análise interrompida.")
                    return
                if res:
                    caminho_imagem, encodings = res
                    all_encodings.extend(encodings)
                    for enc in encodings:
                        encoding_to_path[tuple(enc)] = caminho_imagem
                
                # *** OTIMIZAÇÃO APLICADA AQUI ***
                # Atualiza a UI apenas a cada 10 imagens para não sobrecarregar
                if i % 10 == 0 or i == total_imagens - 1:
                    progresso = 0.1 + (i / total_imagens) * 0.6
                    self.app.after(0, self.app.progressbar.set, progresso)

        if not all_encodings:
            self.app.after(0, self.app.finalizar_busca, "Nenhum rosto encontrado.")
            return

        self.app.after(0, self.app.atualizar_status, "Passo 3/4: Criando grupos...", 0.7)
        clt = DBSCAN(metric="euclidean", n_jobs=-1, eps=eps, min_samples=min_fotos_por_grupo)
        clt.fit(all_encodings)
        
        self.app.after(0, self.app.atualizar_status, "Passo 4/4: Copiando arquivos...", 0.9)
        labelIDs = np.unique(clt.labels_)
        base_destino = self.app.caminho_pasta_destino if self.app.caminho_pasta_destino else self.app.caminho_pasta_fotos
        
        num_grupos_principais = len(np.where(labelIDs > -1)[0])
        for labelID in labelIDs:
            if self.app.stop_event.is_set(): break
            if labelID == -1: continue
            idxs = np.where(clt.labels_ == labelID)[0]
            pasta_pessoa = os.path.join(base_destino, f"Pessoa_{labelID + 1:02d}")
            os.makedirs(pasta_pessoa, exist_ok=True)
            paths_to_copy = {encoding_to_path[tuple(all_encodings[i])] for i in idxs}
            for path in paths_to_copy:
                dest_path = os.path.join(pasta_pessoa, os.path.basename(path))
                if not os.path.exists(dest_path):
                    shutil.copy(path, dest_path)
                    self.app.after(0, self.app.adicionar_preview_foto, dest_path, f"{os.path.basename(path)} -> Pessoa_{labelID + 1:02d}")

        # *** LÓGICA DE CÓPIA DOS ISOLADOS CORRIGIDA AQUI ***
        outlier_idxs = np.where(clt.labels_ == -1)[0]
        num_isolados = 0
        if len(outlier_idxs) > 0:
            pasta_isolados_parent = os.path.join(base_destino, "_Rostos Isolados")
            os.makedirs(pasta_isolados_parent, exist_ok=True)
            
            # Mapeia cada codificação de rosto isolado ao seu arquivo de origem
            isolated_paths = [encoding_to_path[tuple(all_encodings[i])] for i in outlier_idxs]
            
            # Copia cada imagem isolada para uma pasta separada, sem duplicatas
            copied_files_in_session = set()
            for path in set(isolated_paths):
                if self.app.stop_event.is_set(): break
                if path in copied_files_in_session: continue
                
                num_isolados += 1
                pasta_sub_isolado = os.path.join(pasta_isolados_parent, f"Rosto_{num_isolados:03d}")
                os.makedirs(pasta_sub_isolado, exist_ok=True)
                
                dest_path = os.path.join(pasta_sub_isolado, os.path.basename(path))
                if not os.path.exists(dest_path):
                     shutil.copy(path, dest_path)
                     self.app.after(0, self.app.adicionar_preview_foto, dest_path, f"Isolados/Rosto_{num_isolados:03d}")
                copied_files_in_session.add(path)

        if self.app.stop_event.is_set():
            self.app.after(0, self.app.finalizar_busca, "Análise interrompida pelo usuário.")
        else:
            self.app.after(0, self.app.finalizar_busca, f"Concluído! {num_grupos_principais} grupos e {num_isolados} rostos isolados encontrados.")

    def executar_busca_individual(self):
        try:
            encodings_ref = face_recognition.face_encodings(face_recognition.load_image_file(self.app.caminho_foto_referencia))
            if not encodings_ref:
                self.app.after(0, self.app.messagebox.showerror, "Erro", "Nenhum rosto encontrado na foto de referência.")
                self.app.after(0, self.app.finalizar_busca, "Busca falhou.")
                return
            person_name = self.app.entry_nome_pessoa.get().strip()
            self.executar_busca_paralela({person_name: encodings_ref[0]})
        except Exception as e:
            self.app.after(0, self.app.finalizar_busca, f"Erro crítico: {e}")

    def executar_busca_lote(self):
        try:
            self.app.after(0, self.app.atualizar_status, "Carregando faces de referência...", 0)
            known_encodings = {}
            ref_files = [f for f in os.listdir(self.app.caminho_pasta_referencia) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            for filename in ref_files:
                person_name, filepath = os.path.splitext(filename)[0], os.path.join(self.app.caminho_pasta_referencia, filename)
                try:
                    encoding = face_recognition.face_encodings(face_recognition.load_image_file(filepath))[0]
                    known_encodings[person_name] = encoding
                except IndexError:
                    continue
            if not known_encodings:
                self.app.after(0, self.app.messagebox.showerror, "Erro", "Nenhum rosto válido encontrado na pasta de referências.")
                self.app.after(0, self.app.finalizar_busca, "Busca falhou.")
                return
            self.executar_busca_paralela(known_encodings)
        except Exception as e:
            self.app.after(0, self.app.finalizar_busca, f"Erro crítico: {e}")

    def executar_busca_paralela(self, known_encodings):
        mapeamento = {"Preciso": 0.5, "Equilibrado": 0.6, "Abrangente": 0.68}
        tolerancia = mapeamento[self.app.seg_button_precisao.get()]
        downscale_factor = self.app.get_downscale_factor()
        base_destino = self.app.caminho_pasta_destino if self.app.caminho_pasta_destino else self.app.caminho_pasta_fotos
        caminhos_imagens = [os.path.join(self.app.caminho_pasta_fotos, f) for f in os.listdir(self.app.caminho_pasta_fotos) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not caminhos_imagens:
            self.app.after(0, self.app.finalizar_busca, "Nenhuma imagem encontrada.")
            return
        
        self.app.after(0, self.app.atualizar_status, f"Analisando {len(caminhos_imagens)} imagens...", 0)
        num_processos = max(1, cpu_count() - 1)
        worker_func = functools.partial(processar_imagem_busca_worker, known_encodings=known_encodings, tolerance=tolerancia, downscale_factor=downscale_factor)
        
        total_imagens = len(caminhos_imagens)
        with Pool(processes=num_processos) as pool:
            resultados = pool.imap_unordered(worker_func, caminhos_imagens)
            for i, res in enumerate(resultados):
                if self.app.stop_event.is_set():
                    pool.terminate()
                    self.app.after(0, self.app.finalizar_busca, "Análise interrompida.")
                    return
                if res:
                    caminho_origem, person_name = res
                    pasta_pessoa = os.path.join(base_destino, person_name)
                    os.makedirs(pasta_pessoa, exist_ok=True)
                    nome_arquivo = os.path.basename(caminho_origem)
                    caminho_destino_arquivo = os.path.join(pasta_pessoa, nome_arquivo)
                    if not os.path.exists(caminho_destino_arquivo):
                        shutil.copy(caminho_origem, caminho_destino_arquivo)
                        self.app.after(0, self.app.adicionar_preview_foto, caminho_destino_arquivo, f"{nome_arquivo} -> {person_name}")
                
                # *** OTIMIZAÇÃO APLICADA AQUI TAMBÉM ***
                if i % 10 == 0 or i == total_imagens - 1:
                    self.app.after(0, self.app.progressbar.set, (i + 1) / total_imagens)

        self.app.after(0, self.app.finalizar_busca, f"Concluído! {len(self.app.scroll_frame.winfo_children())} foto(s) encontrada(s).")