import customtkinter as ctk
from tkinter import filedialog, messagebox, Menu
import os
import shutil
import threading
import json
import subprocess
import sys
from PIL import Image, ImageTk

from ..core.processing import ProcessingEngine

CONFIG_FILE = "fotofinder_config.json"

class PhotoFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FotoFinder Pro")
        self.geometry("1280x760")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.engine = ProcessingEngine(self)
        self.stop_event = threading.Event()
        self.processing_thread = None

        # --- Variáveis de Estado da UI e Resultados ---
        self.results_data = {}  # Dicionário para armazenar os resultados: {'Grupo': ['path1', 'path2']}
        self.thumbnail_widgets = {} # Mapeia file_path para seu widget de card
        self.selected_items = set() # Conjunto de file_paths selecionados
        self.thumbnail_size = ctk.IntVar(value=120)
        
        self.min_fotos_var = ctk.StringVar(value="2")
        self.downscale_var = ctk.StringVar(value="Rápido")
        self.precisao_var = ctk.StringVar(value="Equilibrado")
        
        self.load_settings()
        self.create_widgets()
        self.apply_loaded_settings()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.on_mode_change()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_content_area()

    def create_sidebar(self):
        sidebar_frame = ctk.CTkFrame(self, width=350, corner_radius=0)
        sidebar_frame.grid(row=0, column=0, sticky="nsw")
        sidebar_frame.pack_propagate(False)

        ctk.CTkLabel(sidebar_frame, text="FotoFinder Pro", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 10))
        
        self.mode_selector = ctk.CTkSegmentedButton(sidebar_frame, values=["Agrupar", "Individual", "Lote"], command=self.on_mode_change)
        self.mode_selector.pack(fill="x", padx=20, pady=10)
        
        self.cluster_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        self.individual_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        self.batch_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        
        self.setup_clustering_mode_controls(self.cluster_frame)
        self.setup_individual_mode_controls(self.individual_frame)
        self.setup_batch_mode_controls(self.batch_frame)

        path_frame = ctk.CTkFrame(sidebar_frame)
        path_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(path_frame, text="Pastas", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5, 10))
        self.btn_selecionar_pasta = ctk.CTkButton(path_frame, text="📁 Pasta de Origem...", command=self.selecionar_pasta_origem)
        self.btn_selecionar_pasta.pack(fill="x", padx=10)
        self.lbl_caminho_origem = ctk.CTkLabel(path_frame, text="Nenhuma pasta selecionada", font=ctk.CTkFont(size=10), wraplength=300)
        self.lbl_caminho_origem.pack(fill="x", padx=10, pady=(0, 5))
        self.btn_selecionar_destino = ctk.CTkButton(path_frame, text="📂 Pasta de Destino...", command=self.selecionar_pasta_destino)
        self.btn_selecionar_destino.pack(fill="x", padx=10, pady=(5,0))
        self.lbl_caminho_destino = ctk.CTkLabel(path_frame, text="Nenhuma pasta selecionada", font=ctk.CTkFont(size=10), wraplength=300)
        self.lbl_caminho_destino.pack(fill="x", padx=10, pady=(0, 10))

        settings_frame = ctk.CTkFrame(sidebar_frame)
        settings_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(settings_frame, text="Configurações da Análise", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5, 10))
        ctk.CTkLabel(settings_frame, text="Otimização de Velocidade:", font=ctk.CTkFont(size=12)).pack(padx=10, anchor="w")
        self.seg_button_downscale = ctk.CTkSegmentedButton(settings_frame, variable=self.downscale_var, values=["Original", "Rápido", "Muito Rápido"])
        self.seg_button_downscale.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(settings_frame, text="Sensibilidade da Análise:", font=ctk.CTkFont(size=12)).pack(padx=10, anchor="w")
        self.seg_button_precisao = ctk.CTkSegmentedButton(settings_frame, variable=self.precisao_var, values=["Preciso", "Equilibrado", "Abrangente"])
        self.seg_button_precisao.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_action = ctk.CTkButton(sidebar_frame, text="🚀 Iniciar Análise", command=self.iniciar_analise, height=45, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_action.pack(side="bottom", fill="x", padx=20, pady=20)
        
        self.settings_widgets = [
            self.mode_selector, self.btn_selecionar_pasta, self.btn_selecionar_destino,
            self.seg_button_downscale, self.seg_button_precisao, self.entry_min_fotos,
            self.btn_selecionar_foto, self.entry_nome_pessoa, self.btn_selecionar_pasta_ref
        ]

    def create_main_content_area(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # --- Barra de Ferramentas de Visualização ---
        toolbar = ctk.CTkFrame(main_frame, height=40)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(toolbar, text="Zoom:").pack(side="left", padx=(10, 5))
        ctk.CTkSlider(toolbar, from_=60, to=250, variable=self.thumbnail_size, command=self.redraw_results_grid).pack(side="left", fill="x", expand=True, padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(main_frame, label_text="Resultados da Análise")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.lbl_no_results = ctk.CTkLabel(self.scroll_frame, text="Os resultados da análise aparecerão aqui.", font=ctk.CTkFont(size=16), text_color="gray")
        self.lbl_no_results.pack(expand=True, padx=20, pady=20)

        # --- Barra de Status ---
        status_bar = ctk.CTkFrame(main_frame, height=30)
        status_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        status_bar.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(status_bar, text="Pronto para iniciar.", anchor="w")
        self.lbl_status.grid(row=0, column=0, sticky="ew", padx=10)
        self.lbl_selection_status = ctk.CTkLabel(status_bar, text="", anchor="center")
        self.lbl_selection_status.grid(row=0, column=1, sticky="ew", padx=10)
        self.progressbar = ctk.CTkProgressBar(status_bar)
        self.progressbar.set(0)
        self.progressbar.grid(row=0, column=2, sticky="e", padx=10, pady=5)

    def redraw_results_grid(self, event=None):
        """Limpa e redesenha toda a grade de resultados com base nos dados e no tamanho do zoom."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.thumbnail_widgets.clear()
        if not self.results_data:
            self.lbl_no_results = ctk.CTkLabel(self.scroll_frame, text="Os resultados da análise aparecerão aqui.", font=ctk.CTkFont(size=16), text_color="gray")
            self.lbl_no_results.pack(expand=True, padx=20, pady=20)
            return
            
        thumb_size = self.thumbnail_size.get()
        padding = 10
        # Força a atualização da largura do frame para um cálculo preciso das colunas
        self.scroll_frame.update_idletasks()
        frame_width = self.scroll_frame.winfo_width() - 20 # Desconta a barra de rolagem
        cols = max(1, frame_width // (thumb_size + padding))
        
        current_row = 0
        for group_name, items in sorted(self.results_data.items()):
            if not items: continue

            # --- Cabeçalho do Grupo ---
            header = ctk.CTkLabel(self.scroll_frame, text=group_name, font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
            header.grid(row=current_row, column=0, columnspan=cols, sticky="ew", pady=(15, 5), padx=5)
            current_row += 1
            
            # --- Grade de Miniaturas ---
            col = 0
            for file_path in items:
                card = self.create_thumbnail_card(self.scroll_frame, file_path, thumb_size)
                card.grid(row=current_row, column=col, padx=padding/2, pady=padding/2)
                
                col += 1
                if col >= cols:
                    col = 0
                    current_row += 1
            current_row += 1 if col == 0 else 2 # Espaçamento extra após o grupo
        
    def create_thumbnail_card(self, parent, file_path, size):
        """Cria um widget 'card' para uma única miniatura."""
        card_border_color = "gray50"
        if file_path in self.selected_items:
            card_border_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"][1]

        card = ctk.CTkFrame(parent, border_width=2, border_color=card_border_color)
        
        try:
            img = Image.open(file_path)
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            
            lbl_img = ctk.CTkLabel(card, image=ctk_img, text="")
            lbl_img.pack(padx=5, pady=5)
            
            filename = os.path.basename(file_path)
            lbl_name = ctk.CTkLabel(card, text=filename, font=ctk.CTkFont(size=10))
            lbl_name.pack(padx=5, pady=(0, 5), fill="x")

            # --- Bindings de Eventos ---
            for widget in [card, lbl_img, lbl_name]:
                widget.bind("<Button-1>", lambda e, p=file_path: self.on_thumbnail_click(e, p))
                widget.bind("<Double-Button-1>", lambda e, p=file_path: self.open_image_viewer(p))
                widget.bind("<Button-3>", lambda e, p=file_path: self.show_context_menu(e, p))
                
        except Exception as e:
            error_lbl = ctk.CTkLabel(card, text=f"Erro ao carregar\n{os.path.basename(file_path)}", wraplength=size)
            error_lbl.pack(padx=5, pady=5, expand=True, fill="both")
        
        self.thumbnail_widgets[file_path] = card
        return card

    # --- Funções de Manipulação de UI ---
    def on_mode_change(self, value=None):
        selected_mode = self.mode_selector.get()
        self.cluster_frame.pack_forget(); self.individual_frame.pack_forget(); self.batch_frame.pack_forget()
        if selected_mode == "Agrupar": self.cluster_frame.pack(fill="x", padx=20)
        elif selected_mode == "Individual": self.individual_frame.pack(fill="x", padx=20)
        elif selected_mode == "Lote": self.batch_frame.pack(fill="x", padx=20)

    def toggle_analysis_state(self, is_running):
        if is_running:
            self.btn_action.configure(text="🛑 Parar Análise", command=self.parar_busca, fg_color="#D32F2F", hover_color="#B71C1C")
            for widget in self.settings_widgets: widget.configure(state="disabled")
        else:
            self.btn_action.configure(text="🚀 Iniciar Análise", command=self.iniciar_analise, fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])
            for widget in self.settings_widgets: widget.configure(state="normal")
            
    # --- Funções de Preparação e Finalização ---
    def preparar_ui_para_busca(self):
        self.stop_event.clear()
        self.toggle_analysis_state(is_running=True)
        self.results_data.clear()
        self.selected_items.clear()
        self.update_selection_status()
        self.redraw_results_grid() # Limpa a tela e mostra a mensagem inicial
        self.progressbar.set(0)

    def finalizar_busca(self, mensagem_final):
        self.toggle_analysis_state(is_running=False)
        if mensagem_final: self.lbl_status.configure(text=mensagem_final)
        self.redraw_results_grid() # Redesenha a grade final com todos os resultados

    def parar_busca(self):
        self.stop_event.set()
        self.lbl_status.configure(text="Parando análise... Por favor, aguarde.")

    def adicionar_preview_foto(self, caminho_foto, texto_display):
        """Adiciona o resultado aos dados e atualiza a UI de forma otimizada."""
        # 'Pessoa_01' from "path -> Pessoa_01"
        group_name = texto_display.split(" -> ")[-1].replace("/", "_") 
        if group_name not in self.results_data:
            self.results_data[group_name] = []
        
        if caminho_foto not in self.results_data[group_name]:
            self.results_data[group_name].append(caminho_foto)
        
        # Para evitar sobrecarga, redesenha a grade a cada X itens.
        total_items = sum(len(v) for v in self.results_data.values())
        if total_items % 10 == 1:
             self.redraw_results_grid()

    # --- Lógica de Interação com a Grade ---
    def on_thumbnail_click(self, event, file_path):
        ctrl_pressed = (event.state & 0x0004) != 0
        card = self.thumbnail_widgets.get(file_path)
        if not card: return

        if not ctrl_pressed: # Clique simples, sem Ctrl
            # Se o item clicado for o único selecionado, deseleciona-o. Senão, seleciona apenas ele.
            if len(self.selected_items) == 1 and file_path in self.selected_items:
                self.selected_items.clear()
                card.configure(border_color="gray50")
            else:
                for path in self.selected_items:
                    if path in self.thumbnail_widgets: self.thumbnail_widgets[path].configure(border_color="gray50")
                self.selected_items.clear()
                self.selected_items.add(file_path)
                card.configure(border_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"][1])
        else: # Clique com Ctrl
            if file_path in self.selected_items:
                self.selected_items.remove(file_path)
                card.configure(border_color="gray50")
            else:
                self.selected_items.add(file_path)
                card.configure(border_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"][1])
        
        self.update_selection_status()

    def update_selection_status(self):
        count = len(self.selected_items)
        if count == 0:
            self.lbl_selection_status.configure(text="")
        elif count == 1:
            self.lbl_selection_status.configure(text="1 item selecionado")
        else:
            self.lbl_selection_status.configure(text=f"{count} itens selecionados")

    def open_image_viewer(self, file_path):
        try:
            if sys.platform == "win32": os.startfile(file_path)
            elif sys.platform == "darwin": subprocess.run(["open", file_path])
            else: subprocess.run(["xdg-open", file_path])
        except Exception as e: messagebox.showerror("Erro", f"Não foi possível abrir a imagem: {e}")

    def show_context_menu(self, event, file_path):
        # Garante que o item clicado com o botão direito esteja na seleção
        if file_path not in self.selected_items:
            self.on_thumbnail_click(event, file_path)
            
        menu = Menu(self, tearoff=0)
        num_selected = len(self.selected_items)
        
        label_abrir = f"Abrir Local do Arquivo" if num_selected == 1 else f"Abrir Local de {num_selected} Arquivos"
        label_excluir = f"Excluir Cópia" if num_selected == 1 else f"Excluir {num_selected} Cópias"
        
        menu.add_command(label=label_abrir, command=self.abrir_local_selecionado)
        menu.add_separator()
        menu.add_command(label=label_excluir, command=self.excluir_copia_selecionada)
        menu.tk_popup(event.x_root, event.y_root)
        
    def abrir_local_selecionado(self):
        # Abre o local do primeiro arquivo selecionado
        if self.selected_items:
            path_to_open = next(iter(self.selected_items))
            folder = os.path.dirname(path_to_open)
            self.open_image_viewer(folder) # Reutiliza a função para abrir a pasta

    def excluir_copia_selecionada(self):
        num_selected = len(self.selected_items)
        if num_selected == 0: return
        
        msg = f"Tem certeza que deseja excluir a cópia selecionada?" if num_selected == 1 else f"Tem certeza que deseja excluir as {num_selected} cópias selecionadas?"
        if messagebox.askyesno("Confirmar Exclusão", msg):
            items_to_delete = list(self.selected_items)
            for file_path in items_to_delete:
                try:
                    os.remove(file_path)
                    widget = self.thumbnail_widgets.pop(file_path, None)
                    if widget: widget.destroy()
                    self.selected_items.remove(file_path)
                    # Remove o dado da fonte para não reaparecer
                    for group in self.results_data:
                        if file_path in self.results_data[group]:
                            self.results_data[group].remove(file_path)
                except Exception as e:
                    messagebox.showerror("Erro", f"Não foi possível excluir o arquivo: {e}")
            self.update_selection_status()

    def iniciar_analise(self):
        # O resto do código (lógica de iniciar, selecionar pastas, salvar/carregar configs, etc.)
        # permanece o mesmo. Cole o restante das funções da versão anterior aqui.
        target_function = None
        modo = self.mode_selector.get()
        
        if modo == "Agrupar":
            if not getattr(self, 'caminho_pasta_fotos', None):
                messagebox.showerror("Campos Incompletos", "Por favor, escolha a Pasta de Origem."); return
            if not messagebox.askyesno("Aviso de Desempenho", "O agrupamento automático pode ser demorado.\nDeseja continuar?"): return
            target_function = self.engine.executar_busca_cluster
            
        elif modo == "Individual":
            if not all([getattr(self, 'caminho_foto_referencia', None), getattr(self, 'caminho_pasta_fotos', None), self.entry_nome_pessoa.get().strip()]):
                messagebox.showerror("Campos Incompletos", "Preencha a foto de referência, nome, e pasta de origem."); return
            target_function = self.engine.executar_busca_individual

        elif modo == "Lote":
            if not all([getattr(self, 'caminho_pasta_referencia', None), getattr(self, 'caminho_pasta_fotos', None)]):
                messagebox.showerror("Campos Incompletos", "Escolha a pasta de referências e a de origem."); return
            target_function = self.engine.executar_busca_lote
        
        if target_function:
            self.preparar_ui_para_busca()
            self.processing_thread = threading.Thread(target=target_function, daemon=True)
            self.processing_thread.start()
            
    # --- Funções de setup da sidebar (inalteradas, mas necessárias) ---
    def setup_clustering_mode_controls(self, parent_frame):
        parent_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(parent_frame, text="Mínimo de fotos por grupo:", font=ctk.CTkFont(size=12)).pack(anchor="w")
        validate_cmd = self.register(self._validate_numeric_input)
        self.entry_min_fotos = ctk.CTkEntry(parent_frame, textvariable=self.min_fotos_var, justify="center", validate="key", validatecommand=(validate_cmd, '%P'))
        self.entry_min_fotos.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(parent_frame, text="Agrupa todas as pessoas automaticamente. Pode ser demorado.", font=ctk.CTkFont(size=10, slant="italic"), wraplength=300, justify="left").pack(anchor="w")
    
    def setup_individual_mode_controls(self, parent_frame):
        parent_frame.pack(fill="x", padx=20)
        self.btn_selecionar_foto = ctk.CTkButton(parent_frame, text="👤 Escolher Foto de Referência", command=self.selecionar_foto_referencia)
        self.btn_selecionar_foto.pack(fill="x")
        self.preview_foto = ctk.CTkLabel(parent_frame, text="", height=80, fg_color=("gray85", "gray19"), corner_radius=5)
        self.preview_foto.pack(fill="x", pady=5)
        self.entry_nome_pessoa = ctk.CTkEntry(parent_frame, placeholder_text="Digite o nome da pessoa")
        self.entry_nome_pessoa.pack(fill="x", pady=5)

    def setup_batch_mode_controls(self, parent_frame):
        parent_frame.pack(fill="x", padx=20)
        self.btn_selecionar_pasta_ref = ctk.CTkButton(parent_frame, text="🗂️ Escolher Pasta de Referências", command=self.selecionar_pasta_referencia)
        self.btn_selecionar_pasta_ref.pack(fill="x")
        self.lbl_caminho_pasta_ref = ctk.CTkLabel(parent_frame, text="Nenhuma pasta selecionada", font=ctk.CTkFont(size=10))
        self.lbl_caminho_pasta_ref.pack()
        ctk.CTkLabel(parent_frame, text="O nome de cada arquivo na pasta de referência será usado como nome da pessoa.", font=ctk.CTkFont(size=10, slant="italic"), wraplength=300, justify="left").pack(pady=5, anchor="w")

    # --- Funções de utilidade e callbacks (restantes) ---
    def _validate_numeric_input(self, proposed_text):
        if proposed_text == "": return True
        if proposed_text.isdigit() and int(proposed_text) > 0: return True
        return False

    def on_closing(self):
        self.save_settings()
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_event.set()
            self.processing_thread.join()
        self.destroy()

    def save_settings(self):
        settings = {"caminho_pasta_fotos": getattr(self, 'caminho_pasta_fotos', None), "caminho_pasta_destino": getattr(self, 'caminho_pasta_destino', None), "nivel_precisao": self.precisao_var.get(), "min_fotos_grupo": self.min_fotos_var.get(), "downscale_option": self.downscale_var.get()}
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump(settings, f, indent=4)
        except Exception as e: print(f"Erro ao salvar configurações: {e}")

    def load_settings(self):
        try:
            with open(CONFIG_FILE, 'r') as f: settings = json.load(f)
            self.caminho_pasta_fotos = settings.get("caminho_pasta_fotos")
            self.caminho_pasta_destino = settings.get("caminho_pasta_destino")
            self.precisao_var.set(settings.get("nivel_precisao", "Equilibrado"))
            self.min_fotos_var.set(settings.get("min_fotos_grupo", "2"))
            self.downscale_var.set(settings.get("downscale_option", "Rápido"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.caminho_pasta_fotos, self.caminho_pasta_destino = None, None

    def apply_loaded_settings(self):
        if self.caminho_pasta_fotos: self.lbl_caminho_origem.configure(text=self.caminho_pasta_fotos)
        if self.caminho_pasta_destino: self.lbl_caminho_destino.configure(text=self.caminho_pasta_destino)
    
    def get_downscale_factor(self):
        option = self.downscale_var.get()
        if "Rápido" == option: return 0.5
        if "Muito Rápido" == option: return 0.25
        return 1.0
        
    def atualizar_status(self, texto, progresso):
        self.lbl_status.configure(text=texto)
        self.progressbar.set(progresso)

    def selecionar_pasta_origem(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta com as fotos")
        if caminho: self.caminho_pasta_fotos = caminho; self.lbl_caminho_origem.configure(text=caminho)

    def selecionar_pasta_destino(self):
        caminho = filedialog.askdirectory(title="Selecione onde salvar as cópias")
        if caminho: self.caminho_pasta_destino = caminho; self.lbl_caminho_destino.configure(text=caminho)

    def selecionar_foto_referencia(self):
        caminho = filedialog.askopenfilename(title="Selecione a foto de referência", filetypes=[("Imagens", "*.jpg *.jpeg *.png")])
        if caminho:
            self.caminho_foto_referencia = caminho
            img = Image.open(caminho)
            img.thumbnail((300, 80))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.preview_foto.configure(image=ctk_img, text="")
    
    def selecionar_pasta_referencia(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta com as fotos de referência")
        if caminho: self.caminho_pasta_referencia = caminho; self.lbl_caminho_pasta_ref.configure(text=caminho)