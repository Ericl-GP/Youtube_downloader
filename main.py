"""
YT Batch Downloader
Autor: baseado no projeto de Ericles Gomes P.
Dependências: pip install yt-dlp customtkinter Pillow requests
"""

import yt_dlp
import customtkinter as ctk
import threading
import os
import sys
import requests
from PIL import Image
from io import BytesIO
from tkinter import messagebox, filedialog
from dataclasses import dataclass, field
from typing import Callable
import queue
import time


# ──────────────────────────────────────────────
#  CONFIGURAÇÃO VISUAL
# ──────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COR_BG       = "#0f0f0f"
COR_CARD     = "#1a1a1a"
COR_ACCENT   = "#ff0033"          # vermelho YouTube
COR_VERDE    = "#00b894"
COR_TEXTO    = "#eeeeee"
COR_CINZA    = "#444444"
COR_PENDING  = "#555555"
COR_OK       = "#00b894"
COR_ERR      = "#e74c3c"
COR_DL       = "#f39c12"


# ──────────────────────────────────────────────
#  ESTRUTURA DE ITEM
# ──────────────────────────────────────────────
@dataclass
class DownloadItem:
    url: str
    title: str = "Carregando..."
    thumbnail_url: str = ""
    status: str = "pendente"   # pendente | baixando | concluído | erro | ignorado
    progress: float = 0.0
    formato: str = "MP3"       # MP3 | MP4
    error_msg: str = ""


# ──────────────────────────────────────────────
#  BACKEND
# ──────────────────────────────────────────────

def extrair_info(url: str) -> dict:
    """Extrai metadados de um único vídeo (sem download)."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def baixar_item(item: DownloadItem, pasta: str, hook: Callable, cookies_file: str = None) -> bool:
    """Realiza o download de um único item (MP3 ou MP4)."""
    os.makedirs(pasta, exist_ok=True)
    saida = os.path.join(pasta, "%(title)s.%(ext)s")

    opts_base = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": saida,
        "progress_hooks": [hook],
        "nooverwrites": True,
    }
    
    # Adiciona cookies do arquivo, se existir
    if cookies_file and os.path.exists(cookies_file):
        opts_base["cookiefile"] = cookies_file

    if item.formato == "MP3":
        opts_base.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:  # MP4
        opts_base.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        })

    try:
        with yt_dlp.YoutubeDL(opts_base) as ydl:
            ydl.download([item.url])
        return True
    except Exception as e:
        item.error_msg = str(e)
        return False


# ──────────────────────────────────────────────
#  CARD DE ITEM NA FILA
# ──────────────────────────────────────────────
class ItemCard(ctk.CTkFrame):
    STATUS_CORES = {
        "pendente":  COR_PENDING,
        "baixando":  COR_DL,
        "concluído": COR_OK,
        "erro":      COR_ERR,
        "ignorado":  COR_CINZA,
    }
    STATUS_ICONES = {
        "pendente":  "⏳",
        "baixando":  "⬇",
        "concluído": "✔",
        "erro":      "✘",
        "ignorado":  "—",
    }

    def __init__(self, master, item: DownloadItem, index: int, on_remove: Callable, on_toggle_fmt: Callable):
        super().__init__(master, fg_color=COR_CARD, corner_radius=8)
        self.item = item
        self.on_remove = on_remove
        self.on_toggle_fmt = on_toggle_fmt
        self.index = index
        self._build()

    def _build(self):
        self.columnconfigure(1, weight=1)

        # Número
        ctk.CTkLabel(self, text=f"{self.index + 1:02d}", width=28,
                     text_color=COR_CINZA, font=("Consolas", 11)).grid(row=0, column=0, padx=(8, 4), pady=6, rowspan=2)

        # Título
        self.lbl_titulo = ctk.CTkLabel(self, text=self.item.title, anchor="w",
                                        font=("Arial", 12), text_color=COR_TEXTO, wraplength=340)
        self.lbl_titulo.grid(row=0, column=1, sticky="ew", padx=4, pady=(6, 0))

        # URL (pequena)
        self.lbl_url = ctk.CTkLabel(self, text=self.item.url[:55] + "..." if len(self.item.url) > 55 else self.item.url,
                                     anchor="w", font=("Consolas", 9), text_color=COR_CINZA)
        self.lbl_url.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 4))

        # Frame direito: formato + status + remover
        fr_dir = ctk.CTkFrame(self, fg_color="transparent")
        fr_dir.grid(row=0, column=2, rowspan=2, padx=8, pady=4)

        # Toggle formato
        self.btn_fmt = ctk.CTkButton(
            fr_dir, text=self.item.formato, width=52, height=24,
            fg_color=COR_ACCENT if self.item.formato == "MP3" else "#3498db",
            font=("Arial", 10, "bold"), corner_radius=4,
            command=self._toggle_fmt
        )
        self.btn_fmt.pack(pady=(0, 4))

        # Status badge
        self.lbl_status = ctk.CTkLabel(
            fr_dir, text=self.STATUS_ICONES[self.item.status],
            width=28, height=24, corner_radius=4,
            fg_color=self.STATUS_CORES[self.item.status],
            font=("Arial", 13)
        )
        self.lbl_status.pack(pady=(0, 4))

        # Botão remover
        self.btn_rm = ctk.CTkButton(
            fr_dir, text="✕", width=28, height=24,
            fg_color="transparent", hover_color="#333",
            text_color=COR_CINZA, font=("Arial", 12),
            command=lambda: self.on_remove(self.item)
        )
        self.btn_rm.pack()

        # Barra de progresso (oculta por padrão)
        self.progress_bar = ctk.CTkProgressBar(self, height=4, corner_radius=2, fg_color="#222",
                                                progress_color=COR_DL)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 6))
        self.progress_bar.grid_remove()

    def _toggle_fmt(self):
        if self.item.status not in ("pendente",):
            return
        self.item.formato = "MP4" if self.item.formato == "MP3" else "MP3"
        self.btn_fmt.configure(
            text=self.item.formato,
            fg_color=COR_ACCENT if self.item.formato == "MP3" else "#3498db"
        )
        self.on_toggle_fmt(self.item)

    def atualizar_status(self, status: str, progress: float = None):
        self.item.status = status
        cor = self.STATUS_CORES.get(status, COR_CINZA)
        icone = self.STATUS_ICONES.get(status, "?")
        self.lbl_status.configure(text=icone, fg_color=cor)

        if status == "baixando":
            self.progress_bar.grid()
            self.progress_bar.configure(progress_color=COR_DL)
            if progress is not None:
                self.progress_bar.set(progress)
        elif status == "concluído":
            self.progress_bar.configure(progress_color=COR_OK)
            self.progress_bar.set(1)
        elif status == "erro":
            self.progress_bar.configure(progress_color=COR_ERR)
        else:
            self.progress_bar.grid_remove()

    def atualizar_titulo(self, titulo: str):
        self.item.title = titulo
        self.lbl_titulo.configure(text=titulo)


# ──────────────────────────────────────────────
#  JANELA PRINCIPAL
# ──────────────────────────────────────────────
class YTBatchDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT Batch Downloader")
        self.geometry("760x820")
        self.minsize(680, 600)
        self.configure(fg_color=COR_BG)

        self._items: list[DownloadItem] = []
        self._cards: list[ItemCard] = []
        self._pasta = os.path.join(os.path.expanduser("~"), "Downloads", "YTDownloads")
        self._cookies_file = None  # arquivo de cookies (opcional)
        self._baixando = False
        self._fila_ui: queue.Queue = queue.Queue()   # thread-safe UI updates
        self._build_ui()
        self._poll_ui()

    # ── UI ──────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ─ Cabeçalho ─
        fr_header = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0)
        fr_header.grid(row=0, column=0, sticky="ew")
        fr_header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            fr_header,
            text="  ▶  YT Batch Downloader",
            font=("Arial", 18, "bold"),
            text_color=COR_ACCENT,
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=16, pady=12)

        # ─ Painel de entrada de links ─
        fr_entrada = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=10)
        fr_entrada.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 0))
        fr_entrada.columnconfigure(0, weight=1)

        ctk.CTkLabel(fr_entrada, text="Cole os links (um por linha):",
                     text_color=COR_CINZA, anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        self.txt_links = ctk.CTkTextbox(fr_entrada, height=110, font=("Consolas", 12),
                                         fg_color="#111", text_color=COR_TEXTO, corner_radius=6)
        self.txt_links.grid(row=1, column=0, sticky="ew", padx=12, pady=0)

        # Formato padrão e botão adicionar
        fr_opcoes = ctk.CTkFrame(fr_entrada, fg_color="transparent")
        fr_opcoes.grid(row=2, column=0, sticky="ew", padx=12, pady=8)

        ctk.CTkLabel(fr_opcoes, text="Formato padrão:").pack(side="left", padx=(0, 8))

        self.seg_fmt = ctk.CTkSegmentedButton(fr_opcoes, values=["MP3", "MP4"], width=140)
        self.seg_fmt.set("MP3")
        self.seg_fmt.pack(side="left")

        ctk.CTkButton(
            fr_opcoes, text="+ Adicionar à fila", width=160, height=32,
            fg_color=COR_VERDE, hover_color="#00a381",
            command=self._adicionar_links
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            fr_opcoes, text="📄 Carregar arquivo", width=140, height=32,
            fg_color="#3498db", hover_color="#2980b9",
            command=self._carregar_arquivo_links
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            fr_opcoes, text="Limpar texto", width=110, height=32,
            fg_color="transparent", border_width=1, border_color=COR_CINZA,
            text_color=COR_CINZA,
            command=lambda: self.txt_links.delete("1.0", "end")
        ).pack(side="right")

        # ─ Fila ─
        fr_fila_label = ctk.CTkFrame(self, fg_color="transparent")
        fr_fila_label.grid(row=2, column=0, sticky="nsew", padx=12, pady=(10, 0))
        fr_fila_label.grid_columnconfigure(0, weight=1)
        fr_fila_label.grid_rowconfigure(1, weight=1)

        # Barra acima da fila: contador + botões de controle da fila
        fr_ctrl_fila = ctk.CTkFrame(fr_fila_label, fg_color="transparent")
        fr_ctrl_fila.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.lbl_contagem = ctk.CTkLabel(fr_ctrl_fila, text="Fila: 0 item(ns)",
                                          text_color=COR_CINZA, font=("Arial", 12))
        self.lbl_contagem.pack(side="left")

        ctk.CTkButton(
            fr_ctrl_fila, text="Todos MP3", width=90, height=26,
            fg_color="transparent", border_width=1, border_color=COR_ACCENT, text_color=COR_ACCENT,
            command=lambda: self._set_formato_todos("MP3")
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            fr_ctrl_fila, text="Todos MP4", width=90, height=26,
            fg_color="transparent", border_width=1, border_color="#3498db", text_color="#3498db",
            command=lambda: self._set_formato_todos("MP4")
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            fr_ctrl_fila, text="Limpar fila", width=90, height=26,
            fg_color="transparent", border_width=1, border_color=COR_CINZA, text_color=COR_CINZA,
            command=self._limpar_fila
        ).pack(side="right", padx=(4, 0))

        # ScrollFrame da fila
        self.scroll_fila = ctk.CTkScrollableFrame(fr_fila_label, fg_color=COR_BG, corner_radius=8)
        self.scroll_fila.grid(row=1, column=0, sticky="nsew")
        self.scroll_fila.columnconfigure(0, weight=1)

        self.lbl_fila_vazia = ctk.CTkLabel(
            self.scroll_fila, text="Cole links acima e clique em '+ Adicionar à fila'",
            text_color=COR_CINZA, font=("Arial", 12)
        )
        self.lbl_fila_vazia.grid(row=0, column=0, pady=40)

        # ─ Rodapé: pasta + botão de download ─
        fr_rodape = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0)
        fr_rodape.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        fr_rodape.columnconfigure(1, weight=1)

        # Pasta de download
        ctk.CTkButton(
            fr_rodape, text="📁", width=36, height=36,
            fg_color="transparent", hover_color="#222",
            command=self._escolher_pasta
        ).grid(row=0, column=0, padx=(12, 4), pady=10)

        self.lbl_pasta = ctk.CTkLabel(fr_rodape, text=self._pasta, anchor="w",
                                       text_color=COR_CINZA, font=("Consolas", 10))
        self.lbl_pasta.grid(row=0, column=1, sticky="ew", padx=4)

        # Cookies
        ctk.CTkButton(
            fr_rodape, text="🍪", width=36, height=36,
            fg_color="transparent", hover_color="#222",
            command=self._escolher_cookies
        ).grid(row=1, column=0, padx=(12, 4), pady=(0, 10))

        self.lbl_cookies = ctk.CTkLabel(fr_rodape, text="Nenhum arquivo de cookies", anchor="w",
                                        text_color=COR_CINZA, font=("Consolas", 10))
        self.lbl_cookies.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 10))

        self.btn_download = ctk.CTkButton(
            fr_rodape, text="⬇  BAIXAR TUDO", width=160, height=40,
            font=("Arial", 13, "bold"),
            fg_color=COR_ACCENT, hover_color="#cc0028",
            command=self._iniciar_downloads
        )
        self.btn_download.grid(row=0, column=2, rowspan=2, padx=12, pady=10)

        self.lbl_global_status = ctk.CTkLabel(fr_rodape, text="", text_color=COR_CINZA,
                                               font=("Arial", 11))
        self.lbl_global_status.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

    # ── LÓGICA DA FILA ───────────────────────

    def _adicionar_links(self):
        texto = self.txt_links.get("1.0", "end").strip()
        if not texto:
            return

        links = [l.strip() for l in texto.splitlines() if l.strip().startswith("http")]
        if not links:
            messagebox.showwarning("Nenhum link", "Nenhum link válido encontrado.\nOs links devem começar com http.")
            return

        self._processar_links(links)

    def _carregar_arquivo_links(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione arquivo com links",
            filetypes=[("Arquivo de texto", "*.txt"), ("Todos", "*.*")],
        )
        if not arquivo:
            return
        
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            links = [l.strip() for l in conteudo.splitlines() if l.strip().startswith("http")]
            if not links:
                messagebox.showwarning("Nenhum link", f"Nenhum link válido encontrado no arquivo.\nOs links devem começar com http.")
                return
            self._processar_links(links)
            messagebox.showinfo("Sucesso", f"Carregados {len(links)} links do arquivo.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivo: {str(e)}")

    def _processar_links(self, links: list[str]):
        """Processa e adiciona links à fila"""
        formato = self.seg_fmt.get()
        novos = []
        
        for url in links:
            # Evita duplicatas
            if any(i.url == url for i in self._items):
                continue
            item = DownloadItem(url=url, formato=formato)
            self._items.append(item)
            novos.append(item)
            self._criar_card(item)

        self._atualizar_contagem()

        # Resolve metadados em background
        if novos:
            threading.Thread(target=self._resolver_metadados, args=(novos,), daemon=True).start()

    def _resolver_metadados(self, itens: list[DownloadItem]):
        for item in itens:
            try:
                info = extrair_info(item.url)
                titulo = info.get("title", item.url)
                thumb = ""
                if info.get("thumbnail"):
                    thumb = info["thumbnail"]
                elif info.get("thumbnails"):
                    thumb = info["thumbnails"][-1]["url"]
                self._fila_ui.put(("meta", item, titulo, thumb))
            except Exception as e:
                self._fila_ui.put(("meta", item, f"[Erro ao carregar] {item.url[:40]}", ""))

    def _criar_card(self, item: DownloadItem):
        idx = len(self._cards)
        self.lbl_fila_vazia.grid_remove()
        card = ItemCard(
            self.scroll_fila, item, idx,
            on_remove=self._remover_item,
            on_toggle_fmt=lambda _: None
        )
        card.grid(row=idx + 1, column=0, sticky="ew", padx=4, pady=3)
        self._cards.append(card)

    def _remover_item(self, item: DownloadItem):
        if self._baixando and item.status == "baixando":
            return
        try:
            idx = self._items.index(item)
        except ValueError:
            return
        self._items.pop(idx)
        card = self._cards.pop(idx)
        card.destroy()
        # Renumera
        for i, c in enumerate(self._cards):
            c.index = i
        if not self._items:
            self.lbl_fila_vazia.grid(row=0, column=0, pady=40)
        self._atualizar_contagem()

    def _limpar_fila(self):
        if self._baixando:
            return
        for c in self._cards:
            c.destroy()
        self._cards.clear()
        self._items.clear()
        self.lbl_fila_vazia.grid(row=0, column=0, pady=40)
        self._atualizar_contagem()

    def _set_formato_todos(self, fmt: str):
        for item, card in zip(self._items, self._cards):
            if item.status == "pendente":
                item.formato = fmt
                card.btn_fmt.configure(
                    text=fmt,
                    fg_color=COR_ACCENT if fmt == "MP3" else "#3498db"
                )

    def _atualizar_contagem(self):
        n = len(self._items)
        concluidos = sum(1 for i in self._items if i.status == "concluído")
        self.lbl_contagem.configure(text=f"Fila: {n} item(ns)  |  Concluídos: {concluidos}")

    def _escolher_pasta(self):
        pasta = filedialog.askdirectory(initialdir=self._pasta, title="Escolha a pasta de destino")
        if pasta:
            self._pasta = pasta
            self.lbl_pasta.configure(text=pasta)

    def _escolher_cookies(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione arquivo de cookies",
            filetypes=[("Arquivo de cookies", "*.txt"), ("Todos", "*.*")],
            initialdir=os.path.dirname(self._pasta) if hasattr(self, '_pasta') else None
        )
        if arquivo:
            self._cookies_file = arquivo
            self.lbl_cookies.configure(text=os.path.basename(arquivo))

    # ── DOWNLOAD ────────────────────────────

    def _iniciar_downloads(self):
        pendentes = [i for i in self._items if i.status in ("pendente", "erro")]
        if not pendentes:
            messagebox.showinfo("Nada para baixar", "Todos os itens já foram baixados ou a fila está vazia.")
            return
        if self._baixando:
            return

        self._baixando = True
        self.btn_download.configure(state="disabled", text="⏸ Baixando...")
        self.lbl_global_status.configure(text=f"0 / {len(pendentes)} concluídos")

        threading.Thread(target=self._thread_downloads, args=(pendentes,), daemon=True).start()

    def _thread_downloads(self, pendentes: list[DownloadItem]):
        total = len(pendentes)

        for n, item in enumerate(pendentes, 1):
            self._fila_ui.put(("status", item, "baixando", 0))
            self._fila_ui.put(("global_status", f"Baixando {n}/{total}: {item.title[:30]}..."))

            def hook(d, _item=item):
                if d["status"] == "downloading":
                    try:
                        perc_str = d.get("_percent_str", "0%").strip().replace("%", "")
                        p = float(perc_str) / 100
                    except (ValueError, TypeError):
                        p = 0.0
                    self._fila_ui.put(("status", _item, "baixando", p))
                elif d["status"] == "finished":
                    self._fila_ui.put(("status", _item, "baixando", 0.99))

            sucesso = baixar_item(item, self._pasta, hook, self._cookies_file)

            if sucesso:
                self._fila_ui.put(("status", item, "concluído", 1))
            else:
                self._fila_ui.put(("status", item, "erro", 0))
                self._fila_ui.put(("global_status", f"Erro em: {item.title[:30]} — {item.error_msg[:60]}"))
                time.sleep(1.5)

        concluidos = sum(1 for i in self._items if i.status == "concluído")
        erros = sum(1 for i in self._items if i.status == "erro")
        self._fila_ui.put(("global_status", f"✔ Concluído! {concluidos} baixados, {erros} erro(s)."))
        self._fila_ui.put(("reset_btn",))

    # ── POLL DE UI (thread-safe) ─────────────

    def _poll_ui(self):
        try:
            while True:
                msg = self._fila_ui.get_nowait()
                tipo = msg[0]

                if tipo == "status":
                    _, item, status, progress = msg
                    card = self._card_para(item)
                    if card:
                        card.atualizar_status(status, progress)
                    self._atualizar_contagem()

                elif tipo == "meta":
                    _, item, titulo, thumb = msg
                    card = self._card_para(item)
                    if card:
                        card.atualizar_titulo(titulo)

                elif tipo == "global_status":
                    self.lbl_global_status.configure(text=msg[1])

                elif tipo == "reset_btn":
                    self._baixando = False
                    self.btn_download.configure(state="normal", text="⬇  BAIXAR TUDO")

        except queue.Empty:
            pass
        self.after(80, self._poll_ui)

    def _card_para(self, item: DownloadItem):
        try:
            idx = self._items.index(item)
            return self._cards[idx]
        except (ValueError, IndexError):
            return None

    def fechar(self):
        sys.exit(0)


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = YTBatchDownloader()
    app.protocol("WM_DELETE_WINDOW", app.fechar)
    app.mainloop()