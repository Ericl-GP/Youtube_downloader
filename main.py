# This is a sample Python script.
import yt_dlp
import os
import yt_dlp as ytdl
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

# Primeira versão, baixar diretamente pelo link infinitamente no formato webm
'''

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


if __name__ == '__main__':
    print_hi('PyCharm')
    video = input(
        'Enter the URL of the video OR the playlist: '  # Mudei o prompt
    )

    ydl_opts = {
        'quiet': True,
        'format': 'bestaudio/best',
        # VAI SALVAR ASSIM: C:/.../Download_yt/[Nome da Playlist]/[01] - [Título do Vídeo].mp3
        'outtmpl': 'C:/Users/ericl/Videos/Download_yt/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s',
        # Remova ou comente a linha 'noplaylist'
        # 'noplaylist': True
    }

    ytdl = yt_dlp.YoutubeDL(ydl_opts)

    print(f" Baixando playlist/video....")
    ytdl.download(video)
    print("Download concluído!")
    '''
# segunda versão, interface e download individual no formato mp3 ou mp4 com previsualização, opção de pular e lista dos proximos
'''

import yt_dlp
import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
import threading
import sys
import webbrowser  # Para o Preview
from tkinter import messagebox

# --- CONFIGURAÇÕES VISUAIS ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
DOWNLOAD_PATH = 'C:/Users/ericl/Videos/Download_yt/%(title)s.%(ext)s'


# --- LÓGICA DE BACKEND (Busca e Download) ---

def buscar_dados(entrada):
    is_link = entrada.startswith("http") or "www." in entrada

    if is_link:
        opts = {
            'quiet': True,
            # 'in_playlist' força a pegar a lista se estiver presente na URL (watch?v=X&list=Y)
            'extract_flat': 'in_playlist',
            'force_generic_extractor': False,
            'noplaylist': False,  # Garante que não vai ignorar o parâmetro &list
            'ignoreerrors': True,  # ESSENCIAL: Pula vídeos removidos/bloqueados no Mix sem travar
        }
    else:
        # Busca 15 resultados
        opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch15',
            'ignoreerrors': True
        }
        entrada = f"ytsearch15:{entrada}"

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(entrada, download=False)

            # Caso 1: Encontrou uma lista (Playlist ou Mix)
            if 'entries' in info:
                # O list() aqui é crucial para converter o gerador do Mix em dados reais
                # Filtramos None porque ignoreerrors=True pode retornar itens vazios
                lista_limpa = [x for x in list(info['entries']) if x is not None]
                return lista_limpa

            # Caso 2: É apenas um vídeo solto
            return [info]

        except Exception as e:
            print(f"Erro na busca: {e}")
            return []


def baixar_conteudo(url, tipo, progress_hook):
    opts = {
        'quiet': True,
        'outtmpl': DOWNLOAD_PATH,
        'progress_hooks': [progress_hook],
        'no_warnings': True,
    }
    if tipo == 'audio':
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except:
        return False


def obter_id_e_thumb(item):
    """Retorna ID e melhor URL de thumb possível"""
    vid_id = item.get('id')
    url_thumb = None

    # Tenta extrair ID da URL se não vier no dict
    if not vid_id:
        u = item.get('url') or item.get('webpage_url')
        if u and "v=" in u: vid_id = u.split("v=")[1].split("&")[0]

    # Define URL da thumb
    if vid_id:
        url_thumb = f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg"  # mqdefault é leve para a sidebar
    elif item.get('thumbnails'):
        url_thumb = item['thumbnails'][-1]['url']

    return vid_id, url_thumb


# --- INTERFACE PRINCIPAL ---

class AppUltimate(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("Youtube Downloader Ultimate Station")
        self.geometry("1000x700")
        self.grid_columnconfigure(0, weight=3)  # Area Video
        self.grid_columnconfigure(1, weight=1)  # Area Playlist
        self.grid_rowconfigure(1, weight=1)  # Conteudo expande, barra de busca fixa

        self.items = []
        self.current_index = 0
        self.sidebar_widgets = []  # Para limpar a sidebar depois

        # === 1. TOPO: BARRA DE BUSCA ===
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)

        self.entry_search = ctk.CTkEntry(self.frame_top, placeholder_text="Cole o Link ou Digite o Nome da Música...",
                                         height=40)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_search = ctk.CTkButton(self.frame_top, text="BUSCAR / CARREGAR", command=self.iniciar_busca, height=40,
                                        fg_color="#3498db")
        self.btn_search.pack(side="left")

        # === 2. ESQUERDA: PLAYER E DOWNLOAD ===
        self.frame_main = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_main.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Capa Grande
        self.frame_img = ctk.CTkFrame(self.frame_main, width=500, height=320, corner_radius=15)
        self.frame_img.pack(pady=10)
        self.lbl_imagem = ctk.CTkLabel(self.frame_img, text="Faça uma busca para começar", width=500, height=320)
        self.lbl_imagem.pack()

        # Título
        self.lbl_titulo = ctk.CTkLabel(self.frame_main, text="...", font=("Arial", 20, "bold"), wraplength=550)
        self.lbl_titulo.pack(pady=(10, 5))

        # Preview Button
        self.btn_preview = ctk.CTkButton(self.frame_main, text="▶ Reproduzir Preview (Navegador)",
                                         fg_color="transparent", border_width=1, border_color="gray",
                                         text_color="white", command=self.abrir_preview)
        self.btn_preview.pack(pady=5)

        # Controles de Download
        self.seg_formato = ctk.CTkSegmentedButton(self.frame_main, values=["Áudio (MP3)", "Vídeo (MP4)"])
        self.seg_formato.set("Áudio (MP3)")
        self.seg_formato.pack(pady=15)

        self.progress = ctk.CTkProgressBar(self.frame_main, width=450)
        self.progress.set(0)
        self.progress.pack(pady=5)
        self.lbl_status = ctk.CTkLabel(self.frame_main, text="")
        self.lbl_status.pack()

        self.frame_btns = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_btns.pack(side="bottom", pady=20)

        self.btn_skip = ctk.CTkButton(self.frame_btns, text="PULAR (Skip)", fg_color="#e74c3c", width=140, height=45,
                                      command=self.pular)
        self.btn_skip.pack(side="left", padx=15)

        self.btn_down = ctk.CTkButton(self.frame_btns, text="BAIXAR", fg_color="#2ecc71", width=140, height=45,
                                      command=self.baixar)
        self.btn_down.pack(side="left", padx=15)

        # === 3. DIREITA: LISTA (SIDEBAR) ===
        self.frame_side = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.frame_side.grid(row=1, column=1, sticky="nsew")

        ctk.CTkLabel(self.frame_side, text="PRÓXIMOS ITENS", font=("Arial", 14, "bold")).pack(pady=10)

        self.scroll_queue = ctk.CTkScrollableFrame(self.frame_side, label_text="Fila")
        self.scroll_queue.pack(fill="both", expand=True, padx=5, pady=5)

        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

    # --- LÓGICA DE INTERFACE ---

    def iniciar_busca(self):
        query = self.entry_search.get()
        if not query: return

        self.btn_search.configure(state="disabled", text="Buscando...")
        self.lbl_imagem.configure(text="Carregando lista...", image=None)

        # Thread para não travar a UI enquanto busca
        threading.Thread(target=self._thread_busca, args=(query,), daemon=True).start()

    def _thread_busca(self, query):
        novos_itens = buscar_dados(query)
        self.after(0, lambda: self._pos_busca(novos_itens))

    def _pos_busca(self, novos_itens):
        self.btn_search.configure(state="normal", text="BUSCAR")

        if not novos_itens:
            messagebox.showerror("Erro", "Nenhum resultado encontrado.")
            return

        self.items = novos_itens
        self.current_index = 0
        self.carregar_item_atual()

    def carregar_item_atual(self):
        # Limpar UI se acabou a lista
        if self.current_index >= len(self.items):
            self.lbl_titulo.configure(text="Fim da Lista")
            self.lbl_imagem.configure(image=None, text="Lista Finalizada")
            self.btn_down.configure(state="disabled")
            self.btn_skip.configure(state="disabled")
            self.btn_preview.configure(state="disabled")
            return

        item = self.items[self.current_index]

        # Resetar visual
        self.lbl_titulo.configure(text=item.get('title', 'Sem Título'))
        self.lbl_status.configure(text=f"Item {self.current_index + 1} de {len(self.items)}")
        self.progress.set(0)
        self.btn_down.configure(state="normal", text="BAIXAR")
        self.btn_skip.configure(state="normal")
        self.btn_preview.configure(state="normal")

        # Thread Imagem Principal
        threading.Thread(target=self._carregar_img_principal, args=(item,), daemon=True).start()

        # Atualizar Sidebar (Em thread separada para carregar as thumbs laterais)
        threading.Thread(target=self._atualizar_sidebar_com_imagens, daemon=True).start()

    def _carregar_img_principal(self, item):
        vid_id, _ = obter_id_e_thumb(item)
        url = f"https://i.ytimg.com/vi/{vid_id}/maxresdefault.jpg" if vid_id else None
        if not url and item.get('thumbnails'): url = item['thumbnails'][-1]['url']

        try:
            if url:
                r = requests.get(url, timeout=3)
                img = Image.open(BytesIO(r.content)).convert("RGB")
                ctk_img = ctk.CTkImage(img, size=(500, 320))
                self.lbl_imagem.configure(image=ctk_img, text="")
            else:
                self.lbl_imagem.configure(image=None, text="[Sem Capa]")
        except:
            pass

    def abrir_preview(self):
        item = self.items[self.current_index]
        url = item.get('webpage_url') or item.get('url')
        if url: webbrowser.open(url)

    def pular(self):
        self.current_index += 1
        self.carregar_item_atual()

    def baixar(self):
        self.btn_down.configure(state="disabled", text="Baixando...")
        self.btn_skip.configure(state="disabled")
        self.progress.start()

        tipo = 'audio' if "Áudio" in self.seg_formato.get() else 'video'
        threading.Thread(target=self._thread_download, args=(tipo,), daemon=True).start()

    def _thread_download(self, tipo):
        item = self.items[self.current_index]
        url = item.get('webpage_url') or item.get('url')
        sucesso = baixar_conteudo(url, tipo, self.progress_hook)
        self.after(0, lambda: self._pos_download(sucesso))

    def _pos_download(self, sucesso):
        self.progress.stop()
        if not sucesso: messagebox.showerror("Erro", "Falha no download.")
        self.current_index += 1
        self.carregar_item_atual()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                p = float(d.get('_percent_str', '0%').replace('%', '')) / 100
                self.progress.set(p)
                self.lbl_status.configure(text=f"Baixando: {int(p * 100)}%")
            except:
                pass
        elif d['status'] == 'finished':
            self.lbl_status.configure(text="Convertendo...")

    # --- LÓGICA DA SIDEBAR (THUMBNAILS) ---
    def _atualizar_sidebar_com_imagens(self):
        # Limpar widgets antigos (Importante fazer isso na thread principal)
        self.after(0, self._limpar_sidebar)

        proximos = self.items[self.current_index + 1: self.current_index + 11]  # Mostra 10 próximos

        for i, item in enumerate(proximos):
            # Preparar dados
            titulo = item.get('title', 'Unknown')[:25] + "..."
            _, url_thumb = obter_id_e_thumb(item)

            # Baixar thumb pequena
            ctk_thumb = None
            if url_thumb:
                try:
                    r = requests.get(url_thumb, timeout=1)
                    pil = Image.open(BytesIO(r.content)).convert("RGB")
                    ctk_thumb = ctk.CTkImage(pil, size=(60, 45))
                except:
                    pass

            # Criar widget na main thread
            self.after(0, lambda t=titulo, img=ctk_thumb, idx=i: self._criar_card_sidebar(t, img, idx))

    def _limpar_sidebar(self):
        for w in self.scroll_queue.winfo_children(): w.destroy()

    def _criar_card_sidebar(self, titulo, img, idx):
        card = ctk.CTkFrame(self.scroll_queue, fg_color="transparent")
        card.pack(fill="x", pady=5)

        # Imagem na esquerda
        lbl_img = ctk.CTkLabel(card, text="[IMG]", image=img, width=60, height=45, fg_color="#1a1a1a")
        if not img: lbl_img.configure(text="No Img")
        lbl_img.pack(side="left", padx=5)

        # Texto na direita
        ctk.CTkLabel(card, text=f"{idx + 1}. {titulo}", font=("Arial", 11), anchor="w").pack(side="left", padx=5)

    def fechar_app(self):
        sys.exit()


if __name__ == "__main__":
    app = AppUltimate()
    app.mainloop()
'''
# com flet para melhor interface e fluides
'''
import flet as ft
import yt_dlp
import threading
import os


# --- BACKEND ---
def buscar_youtube(termo):
    is_link = "http" in termo
    opts = {'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True, 'default_search': 'ytsearch15'}
    if not is_link: termo = f"ytsearch15:{termo}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(termo, download=False)
            if 'entries' in info: return [x for x in list(info['entries']) if x is not None]
            return [info]
        except:
            return []


def obter_link_direto_stream(url_youtube):
    """Pega a URL real do arquivo .mp4 para streaming"""
    # Tenta pegar formato compatível com streaming direto
    opts = {'quiet': True, 'format': 'best[ext=mp4]/best'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_youtube, download=False)
            return info.get('url')
    except:
        return None


def baixar_arquivo(url, tipo, progress_callback):
    path_padrao = os.path.join(os.path.expanduser('~'), 'Downloads', 'YtDownloads', '%(title)s.%(ext)s')
    opts = {'quiet': True, 'outtmpl': path_padrao, 'progress_hooks': [progress_callback], 'no_warnings': True}
    if tipo == 'MP3':
        opts.update({'format': 'bestaudio/best', 'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
    else:
        opts.update(
            {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except:
        return False


# --- FRONTEND ---
def main(page: ft.Page):
    page.title = "Youtube Studio Downloader (Com Preview)"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1100
    page.window_height = 800
    page.padding = 20

    current_items = []
    selected_indices = set()
    current_view_index = 0
    is_downloading = False

    # --- COMPONENTES UI ---

    txt_busca = ft.TextField(hint_text="Busca...", expand=True, border_radius=10)
    btn_busca = ft.ElevatedButton("Buscar", icon=ft.Icons.SEARCH, height=50)

    # --- PLAYER DE PREVIEW ---
    container_midia = ft.Container(
        width=640, height=360,
        bgcolor="black",
        border_radius=15,
        alignment=ft.alignment.center,
        clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

    img_capa = ft.Image(src="", width=640, height=360, fit=ft.ImageFit.COVER, opacity=1)
    btn_play_overlay = ft.IconButton(icon=ft.Icons.PLAY_CIRCLE_FILL, icon_size=80, icon_color="white", opacity=0.8)

    video_player = ft.Video(
        playlist=[],  # Inicializa vazio
        width=640, height=360,
        autoplay=True,
        aspect_ratio=16 / 9,
        volume=100,
    )

    stack_midia = ft.Stack([
        img_capa,
        ft.Container(content=btn_play_overlay, alignment=ft.alignment.center),
        video_player
    ])
    container_midia.content = stack_midia
    video_player.visible = False

    txt_titulo = ft.Text("...", size=20, weight="bold", text_align="center", no_wrap=True,
                         overflow=ft.TextOverflow.ELLIPSIS)
    progress_bar = ft.ProgressBar(width=640, value=0, color="green", bgcolor="#333333")
    txt_status = ft.Text("", color="grey")

    radio_tipo = ft.RadioGroup(
        content=ft.Row([ft.Radio(value="MP3", label="Áudio"), ft.Radio(value="MP4", label="Vídeo")]), value="MP3")

    btn_baixar = ft.ElevatedButton("Baixar Este", icon=ft.Icons.DOWNLOAD, bgcolor="green", color="white")
    btn_prev = ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS, icon_size=30)
    btn_next = ft.IconButton(icon=ft.Icons.SKIP_NEXT, icon_size=30)

    lv_resultados = ft.ListView(expand=True, spacing=10, padding=10)
    btn_baixar_lote = ft.ElevatedButton("Baixar Selecionados", icon=ft.Icons.PLAYLIST_ADD_CHECK, bgcolor="purple",
                                        color="white", expand=True)

    # --- LÓGICA DO PREVIEW CORRIGIDA ---
    def resetar_player():
        """Volta para o estado de capa"""
        # CORREÇÃO 1: Usar .clear() em vez de atribuir lista vazia
        video_player.playlist.clear()
        video_player.visible = False
        img_capa.visible = True
        btn_play_overlay.visible = True
        page.update()

    def tocar_preview(e):
        if not current_items: return

        item = current_items[current_view_index]
        url_youtube = item.get('webpage_url') or item.get('url')

        btn_play_overlay.visible = False
        page.update()

        def _thread_get_stream():
            stream_url = obter_link_direto_stream(url_youtube)

            if stream_url:
                # CORREÇÃO 2: Limpar e adicionar, não substituir a lista
                video_player.playlist.clear()
                video_player.playlist.append(ft.VideoMedia(stream_url))

                video_player.visible = True
                img_capa.visible = False
                page.update()
            else:
                btn_play_overlay.visible = True
                page.snack_bar = ft.SnackBar(ft.Text("Erro ao carregar preview. Vídeo restrito?"))
                page.snack_bar.open = True
                page.update()

        threading.Thread(target=_thread_get_stream, daemon=True).start()

    btn_play_overlay.on_click = tocar_preview

    # --- FUNÇÕES UI GERAIS ---
    def carregar_item_principal(index):
        if not current_items or index < 0 or index >= len(current_items): return
        nonlocal current_view_index

        resetar_player()

        current_view_index = index
        item = current_items[index]

        thumb = "https://via.placeholder.com/640"
        if item.get('thumbnails'): thumb = item['thumbnails'][-1]['url']

        img_capa.src = thumb
        txt_titulo.value = item.get('title', 'Sem titulo')
        txt_status.value = "Pronto."
        progress_bar.value = 0
        page.update()

    def criar_item_lista(item, index):
        def on_check(e):
            if e.control.value:
                selected_indices.add(index)
            else:
                selected_indices.discard(index)

        def on_click(e):
            carregar_item_principal(index)

        thumb = "https://via.placeholder.com/100"
        if item.get('thumbnails'): thumb = item['thumbnails'][0]['url']

        return ft.Container(
            content=ft.Row([
                ft.Checkbox(on_change=on_check),
                ft.Image(src=thumb, width=80, height=45, fit=ft.ImageFit.COVER, border_radius=5),
                ft.Text(f"{index + 1}. {item.get('title', '')}", size=12, expand=True, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS)
            ]),
            bgcolor="#252525", padding=5, border_radius=8, on_click=on_click, ink=True
        )

    # --- BUSCA E DOWNLOAD ---
    def on_buscar_click(e):
        termo = txt_busca.value
        if not termo: return
        btn_busca.disabled = True
        txt_status.value = "Buscando..."
        lv_resultados.controls.clear()
        current_items.clear()
        selected_indices.clear()
        resetar_player()
        page.update()

        def tarefa():
            res = buscar_youtube(termo)
            current_items.extend(res)
            for i, x in enumerate(current_items): lv_resultados.controls.append(criar_item_lista(x, i))
            btn_busca.disabled = False
            if current_items:
                carregar_item_principal(0)
            else:
                txt_status.value = "Nada encontrado"
            page.update()

        threading.Thread(target=tarefa, daemon=True).start()

    def hook_progresso(d):
        if d['status'] == 'downloading':
            try:
                p = float(d.get('_percent_str', '0%').replace('%', '')) / 100
                progress_bar.value = p
                page.update()
            except:
                pass
        elif d['status'] == 'finished':
            txt_status.value = "Finalizando..."
            page.update()

    def executar_downloads(lista):
        nonlocal is_downloading
        if is_downloading: return

        resetar_player()

        is_downloading = True
        btn_baixar.disabled = True
        btn_baixar_lote.disabled = True
        page.update()

        def thread():
            for i, item in enumerate(lista):
                txt_status.value = f"Baixando ({i + 1}/{len(lista)}): {item.get('title')[:20]}..."
                progress_bar.value = 0
                page.update()
                url = item.get('webpage_url') or item.get('url')
                baixar_arquivo(url, radio_tipo.value, hook_progresso)

            txt_status.value = "Concluído!"
            progress_bar.value = 1
            btn_baixar.disabled = False
            btn_baixar_lote.disabled = False
            nonlocal is_downloading
            is_downloading = False
            page.update()

        threading.Thread(target=thread, daemon=True).start()

    btn_busca.on_click = on_buscar_click
    btn_prev.on_click = lambda e: carregar_item_principal(current_view_index - 1)
    btn_next.on_click = lambda e: carregar_item_principal(current_view_index + 1)
    btn_baixar.on_click = lambda e: executar_downloads([current_items[current_view_index]]) if current_items else None

    def on_batch(e):
        if not selected_indices: return
        executar_downloads([current_items[i] for i in sorted(selected_indices)])

    btn_baixar_lote.on_click = on_batch

    # --- LAYOUT ---
    col_esq = ft.Column([
        container_midia,
        progress_bar, txt_titulo, txt_status, radio_tipo,
        ft.Row([btn_prev, btn_baixar, btn_next], alignment="center", spacing=20)
    ], expand=3, alignment="center", horizontal_alignment="center")

    col_dir = ft.Column([ft.Text("Fila", size=16, weight="bold"), btn_baixar_lote, ft.Divider(), lv_resultados],
                        expand=2)

    page.add(
        ft.Row([txt_busca, btn_busca]), ft.Divider(),
        ft.Row(
            [ft.Container(col_esq, padding=10, border=ft.border.all(1, "#444"), border_radius=10), ft.VerticalDivider(),
             col_dir], expand=True)
    )


if __name__ == "__main__":
    ft.app(target=main)
    
    '''

 #versão definitiva, com buscador de local de download e previwe

import flet as ft
import yt_dlp
import threading
import os
import traceback


# --- BACKEND ---

def buscar_youtube(termo):
    is_link = "http" in termo
    opts = {'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True, 'default_search': 'ytsearch15'}
    if not is_link: termo = f"ytsearch15:{termo}"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(termo, download=False)
            if 'entries' in info: return [x for x in list(info['entries']) if x is not None]
            return [info]
    except:
        return []


def obter_link_direto_stream(url_youtube):
    """Obtém link direto MP4 para o player de vídeo"""
    opts = {'quiet': True, 'format': 'best[ext=mp4]/best'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_youtube, download=False)
            return info.get('url')
    except:
        return None


def baixar_arquivo(url, tipo, progress_callback, pasta_destino):
    if not pasta_destino: pasta_destino = os.path.join(os.path.expanduser('~'), 'Downloads')
    path_final = os.path.join(pasta_destino, '%(title)s.%(ext)s')

    opts = {'quiet': True, 'outtmpl': path_final, 'progress_hooks': [progress_callback], 'no_warnings': True}

    if tipo == 'MP3':
        opts.update({'format': 'bestaudio/best', 'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
    else:
        opts.update(
            {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'})

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"Erro DL: {e}")
        return False


# --- FRONTEND ---

def main(page: ft.Page):
    page.title = "Youtube Downloader Ultimate - Made By: Ericles Gomes P."
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1100
    page.window_height = 850
    page.padding = 20

    # Estado
    current_items = []
    current_view_index = 0
    selected_indices = set()
    is_downloading = False
    pasta_padrao = os.path.join(os.path.expanduser('~'), 'Downloads')

    # --- COMPONENTES ---

    # 1. Pasta
    txt_diretorio = ft.TextField(value=pasta_padrao, label="Salvar em", read_only=True, expand=True, height=45)

    def on_dir(e: ft.FilePickerResultEvent):
        if e.path:
            txt_diretorio.value = e.path
            page.update()

    file_picker = ft.FilePicker(on_result=on_dir)
    page.overlay.append(file_picker)
    btn_folder = ft.IconButton(icon=ft.Icons.FOLDER, on_click=lambda _: file_picker.get_directory_path())

    # 2. Busca
    txt_busca = ft.TextField(hint_text="Nome ou Link...", expand=True)
    btn_busca = ft.ElevatedButton("Buscar", icon=ft.Icons.SEARCH, height=45)

    # 3. Player (Imagem + Vídeo com Stack)
    img_capa = ft.Image(src="https://via.placeholder.com/640x360", width=640, height=360, fit=ft.ImageFit.COVER)
    btn_play = ft.IconButton(icon=ft.Icons.PLAY_CIRCLE_FILL, icon_size=80, icon_color="white", opacity=0.8)

    # O Player começa vazio e invisível
    video_player = ft.Video(playlist=[], width=640, height=360, autoplay=True, aspect_ratio=16 / 9, volume=100)
    video_player.visible = False

    # Container Fixo para evitar colapso
    container_midia = ft.Container(
        content=ft.Stack([
            img_capa,
            ft.Container(content=btn_play, alignment=ft.alignment.center),
            video_player
        ]),
        width=640, height=360, bgcolor="black", border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        alignment=ft.alignment.center
    )

    # 4. Info e Controles
    txt_titulo = ft.Text("...", size=18, weight="bold", no_wrap=True, text_align="center")
    progress_bar = ft.ProgressBar(width=640, value=0, color="green", bgcolor="#333")
    txt_status = ft.Text("Pronto.", color="grey")

    radio_tipo = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="MP3", label="MP3"), ft.Radio(value="MP4", label="MP4")
    ]), value="MP3")

    btn_baixar = ft.ElevatedButton("Baixar Atual", icon=ft.Icons.DOWNLOAD, bgcolor="green", color="white")
    btn_prev = ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS, icon_size=30)
    btn_next = ft.IconButton(icon=ft.Icons.SKIP_NEXT, icon_size=30)

    # 5. Lista
    lv_resultados = ft.ListView(expand=True, spacing=5, padding=10)
    btn_lote = ft.ElevatedButton("Baixar Selecionados", bgcolor="purple", color="white")

    # --- LÓGICA ---

    def resetar_player():
        """Volta para a capa e esconde o vídeo"""
        try:
            video_player.playlist.clear()  # Forma correta de limpar no Flet novo
            video_player.visible = False
            img_capa.visible = True
            btn_play.visible = True
            page.update()
        except:
            pass

    def carregar_visual(index):
        if not current_items or index < 0 or index >= len(current_items): return
        nonlocal current_view_index

        resetar_player()  # Importante: reseta ao mudar de item

        current_view_index = index
        item = current_items[index]

        thumb = "https://via.placeholder.com/640"
        if item.get('thumbnails'): thumb = item['thumbnails'][-1]['url']

        img_capa.src = thumb
        txt_titulo.value = item.get('title', 'Sem Título')
        progress_bar.value = 0
        txt_status.value = "Pronto."
        page.update()

    def on_play_click(e):
        if not current_items: return
        item = current_items[current_view_index]
        url = item.get('webpage_url') or item.get('url')

        btn_play.visible = False
        txt_status.value = "Carregando Preview..."
        page.update()

        def _thread_stream():
            stream_url = obter_link_direto_stream(url)
            if stream_url:
                # Adiciona à playlist
                video_player.playlist.clear()
                video_player.playlist.append(ft.VideoMedia(stream_url))

                video_player.visible = True
                img_capa.visible = False
                txt_status.value = "Reproduzindo Preview"
            else:
                btn_play.visible = True
                txt_status.value = "Erro no Preview (Vídeo Restrito?)"
            page.update()

        threading.Thread(target=_thread_stream, daemon=True).start()

    btn_play.on_click = on_play_click

    def on_buscar(e):
        termo = txt_busca.value
        if not termo: return

        btn_busca.disabled = True
        txt_status.value = "Buscando..."
        lv_resultados.controls.clear()
        current_items.clear()
        selected_indices.clear()
        resetar_player()
        page.update()

        def _thread():
            res = buscar_youtube(termo)
            current_items.extend(res)

            for i, item in enumerate(current_items):
                thumb_s = item['thumbnails'][0]['url'] if item.get('thumbnails') else ""

                def on_chk(e, idx=i):
                    if e.control.value:
                        selected_indices.add(idx)
                    else:
                        selected_indices.discard(idx)

                def on_click(e, idx=i):
                    carregar_visual(idx)

                row = ft.Container(
                    content=ft.Row([
                        ft.Checkbox(on_change=on_chk),
                        ft.Image(src=thumb_s, width=60, height=40, fit=ft.ImageFit.COVER, border_radius=4),
                        ft.Text(f"{i + 1}. {item.get('title')}", size=12, no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS, expand=True)
                    ]),
                    padding=5, bgcolor="#222", border_radius=5, on_click=on_click, ink=True
                )
                lv_resultados.controls.append(row)

            if current_items:
                carregar_visual(0)
                txt_status.value = f"{len(current_items)} encontrados."
            else:
                txt_status.value = "Nada encontrado."

            btn_busca.disabled = False
            page.update()

        threading.Thread(target=_thread, daemon=True).start()

    def on_download(e, lote=False):
        # Lógica de definir lista
        lista = []
        if lote:
            if not selected_indices: return
            lista = [current_items[i] for i in sorted(selected_indices)]
        else:
            if current_items: lista = [current_items[current_view_index]]

        if not lista: return

        # Trava UI
        resetar_player()  # Para o vídeo para não gastar internet junto com download
        btn_baixar.disabled = True
        btn_lote.disabled = True
        txt_status.value = "Iniciando..."
        page.update()

        caminho = txt_diretorio.value
        formato = radio_tipo.value

        def _hook(d):
            if d['status'] == 'downloading':
                try:
                    p = float(d.get('_percent_str', '0%').replace('%', '')) / 100
                    progress_bar.value = p
                    page.update()
                except:
                    pass

        def _thread_dl():
            for idx, item in enumerate(lista):
                txt_status.value = f"Baixando ({idx + 1}/{len(lista)}): {item.get('title')[:15]}..."
                progress_bar.value = 0
                page.update()

                url = item.get('webpage_url') or item.get('url')
                baixar_arquivo(url, formato, _hook, caminho)

            txt_status.value = "Concluído!"
            progress_bar.value = 1
            btn_baixar.disabled = False
            btn_lote.disabled = False
            page.update()

        threading.Thread(target=_thread_dl, daemon=True).start()

    # Eventos Botões
    btn_busca.on_click = on_buscar
    btn_prev.on_click = lambda e: carregar_visual(current_view_index - 1)
    btn_next.on_click = lambda e: carregar_visual(current_view_index + 1)
    btn_baixar.on_click = lambda e: on_download(e, lote=False)
    btn_lote.on_click = lambda e: on_download(e, lote=True)

    # --- LAYOUT SEGURO ---

    # Coluna Esquerda com largura fixa (650px) para caber o vídeo de 640px
    left_col = ft.Column([
        container_midia,
        progress_bar,
        txt_titulo,
        txt_status,
        ft.Row([txt_diretorio, btn_folder]),
        radio_tipo,
        ft.Row([btn_prev, btn_baixar, btn_next], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
    ], width=650, scroll=ft.ScrollMode.AUTO)

    right_col = ft.Column([
        ft.Text("Resultados", size=16, weight="bold"),
        btn_lote,
        ft.Divider(),
        lv_resultados
    ], expand=True)

    page.add(
        ft.Row([txt_busca, btn_busca]),
        ft.Divider(),
        ft.Row([left_col, ft.VerticalDivider(), right_col], expand=True)
    )


if __name__ == "__main__":
    ft.app(target=main)