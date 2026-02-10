from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QGraphicsOpacityEffect, QFrame
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont
import cv2
from enum import Enum

from ui_qt.video_widget import VideoWidget
from ui_qt.menu_overlay import MenuOverlay


class TextState(Enum):
    """Estados possíveis de exibição de texto"""
    IDLE = "idle"
    SHOWING_DATE = "showing_date"
    SHOWING_EMOTIONAL = "showing_emotional"
    SHOWING_TITLE = "showing_title"
    SHOWING_HUD = "showing_hud"


class MemoryCard(QFrame):
    """Cartinha de memória coletável"""
    def __init__(self, parent, locked=True):
        super().__init__(parent)
        self.locked = locked
        self.setFixedSize(120, 160)
        
        self.image_label = QLabel(self)
        self.image_label.setGeometry(10, 10, 100, 120)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        if locked:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2a2030;
                    border: 3px solid #4a3a5a;
                }
            """)
            self.image_label.setStyleSheet("""
                color: #5a4a6a;
                font-family: 'Press Start 2P';
                font-size: 40px;
            """)
            self.image_label.setText("?")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #3a2a4a;
                    border: 3px solid #8B4789;
                }
            """)
            # ⚠️ LUGAR PARA COLOCAR A IMAGEM DA SUA IRMÃ:
            # self.image_label.setPixmap(QPixmap("assets/memoria_X.png"))
            self.image_label.setStyleSheet("""
                color: #D4AF37;
                font-family: 'Press Start 2P';
                font-size: 14px;
            """)
            self.image_label.setText("♥")
    
    def unlock(self):
        """Desbloqueia a cartinha com animação"""
        self.locked = False
        self.setStyleSheet("""
            QFrame {
                background-color: #3a2a4a;
                border: 3px solid #D4AF37;
            }
        """)
        self.image_label.setStyleSheet("""
            color: #D4AF37;
            font-family: 'Press Start 2P';
            font-size: 14px;
        """)
        self.image_label.setText("♥")
        
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(500)
        anim.setStartValue(0.3)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutBounce)
        anim.start(QPropertyAnimation.DeleteWhenStopped)


class MainWindow(QMainWindow):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.current_phase_displayed = None
        self.menu_mode = True
        
        # ===== SISTEMA ROBUSTO DE CONTROLE DE TEXTOS =====
        self.text_state = TextState.IDLE
        self.pending_intro = None
        self.shown_complete_for_phase = -1
        
        # ----------------- CONTAINER -----------------
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container.setStyleSheet("background-color: #1a1520;")

        # ----------------- VIDEO (800x800) -----------------
        self.video = VideoWidget(self.container)
        self.video_size = 800
        self.video.setFixedSize(self.video_size, self.video_size)
        self.video.play_file("assets/prolog.mp4", loop=True)
        
        # Conecta sinal de vídeo terminado
        self.video.finished.connect(self._on_video_finished)

        # ----------------- DECORAÇÕES -----------------
        self.deco_tl = QLabel(self.container)
        self.deco_tl.setStyleSheet("color: #B565D8; font-size: 32px;")
        self.deco_tl.setText("♥")
        
        self.deco_tr = QLabel(self.container)
        self.deco_tr.setStyleSheet("color: #D4AF37; font-size: 32px;")
        self.deco_tr.setText("♥")
        
        self.deco_bl = QLabel(self.container)
        self.deco_bl.setStyleSheet("color: #D4AF37; font-size: 32px;")
        self.deco_bl.setText("♥")
        
        self.deco_br = QLabel(self.container)
        self.deco_br.setStyleSheet("color: #B565D8; font-size: 32px;")
        self.deco_br.setText("♥")

        # ----------------- MENU -----------------
        self.menu_overlay = MenuOverlay(self.container)
        self.menu_overlay.raise_()

        # ----------------- HUD FIXO NO TOPO -----------------
        self.hud_bar = QWidget(self.container)
        self.hud_bar.setStyleSheet("background-color: transparent;")
        self.hud_bar.setFixedHeight(100)

        self.hud_title = QLabel("", self.hud_bar)
        self.hud_title.setFont(QFont("Press Start 2P", 18, QFont.Bold))
        self.hud_title.setStyleSheet("""
            color: #D4AF37;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.hud_title.setAlignment(Qt.AlignCenter)

        self.hud_subtitle = QLabel("", self.hud_bar)
        self.hud_subtitle.setFont(QFont("Press Start 2P", 10))
        self.hud_subtitle.setStyleSheet("""
            color: #B565D8;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.hud_subtitle.setAlignment(Qt.AlignCenter)

        self.progress_label = QLabel("", self.hud_bar)
        self.progress_label.setFont(QFont("Press Start 2P", 12))
        self.progress_label.setStyleSheet("""
            color: #8B4789;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)

        self.hud_bar.hide()

        # ----------------- MEMÓRIAS -----------------
        self.memories_container = QWidget(self.container)
        self.memories_container.setStyleSheet("background-color: transparent;")
        
        self.memories_title = QLabel("MEMORIAS", self.memories_container)
        self.memories_title.setFont(QFont("Press Start 2P", 12))
        self.memories_title.setStyleSheet("""
            color: #D4AF37;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.memories_title.setGeometry(0, 0, 200, 30)
        
        self.memories_count = QLabel("0/3", self.memories_container)
        self.memories_count.setFont(QFont("Press Start 2P", 10))
        self.memories_count.setStyleSheet("""
            color: #B565D8;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.memories_count.setGeometry(0, 35, 200, 25)
        
        self.memory_cards = []
        for i in range(3):
            card = MemoryCard(self.memories_container, locked=True)
            card.move(10, 70 + i * 180)
            self.memory_cards.append(card)
        
        self.memories_container.hide()

        # ----------------- OVERLAYS DE TEXTO -----------------
        self.date_overlay = QLabel("", self.container)
        self.date_overlay.setFont(QFont("Press Start 2P", 24))
        self.date_overlay.setStyleSheet("""
            color: #D4AF37;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.date_overlay.setAlignment(Qt.AlignCenter)
        self.date_overlay.hide()

        self.emotional_overlay = QLabel("", self.container)
        self.emotional_overlay.setFont(QFont("Press Start 2P", 16))
        self.emotional_overlay.setStyleSheet("""
            color: #B565D8;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.emotional_overlay.setAlignment(Qt.AlignCenter)
        self.emotional_overlay.hide()

        self.floating_text = QLabel("", self.container)
        self.floating_text.setFont(QFont("Press Start 2P", 32, QFont.Bold))
        self.floating_text.setStyleSheet("""
            color: #FFD700;
            background-color: transparent;
            font-family: 'Press Start 2P', monospace;
        """)
        self.floating_text.setAlignment(Qt.AlignCenter)
        self.floating_text.hide()

        # ----------------- CAM LABEL -----------------
        self.cam_label = QLabel(self.container)
        self.cam_label.setFixedSize(320, 240)
        self.cam_label.setStyleSheet("""
            background: #0a0a0f;
            border: 3px solid #5a4a6a;
        """)
        self.cam_label.raise_()

        self._update_positions()

    def resizeEvent(self, event):
        self._update_positions()
        super().resizeEvent(event)

    def _update_positions(self):
        w = self.container.width()
        h = self.container.height()

        self.deco_tl.move(30, 30)
        self.deco_tr.move(w - 60, 30)
        self.deco_bl.move(30, h - 60)
        self.deco_br.move(w - 60, h - 60)

        self.hud_bar.setGeometry(0, 0, w, 100)
        self.hud_title.setGeometry(0, 20, w, 40)
        self.hud_subtitle.setGeometry(0, 65, w, 25)
        
        self.progress_label.adjustSize()
        self.progress_label.move(w - self.progress_label.width() - 30, 30)

        video_x = (w - self.video_size) // 2
        video_y = (h - self.video_size) // 2
        self.video.move(video_x, video_y)

        memories_x = video_x - 160
        memories_y = video_y
        self.memories_container.setGeometry(memories_x, memories_y, 140, 600)

        cam_margin = 30
        cam_x = w - self.cam_label.width() - cam_margin
        cam_y = h - self.cam_label.height() - cam_margin
        self.cam_label.move(cam_x, cam_y)

        self.floating_text.setGeometry(0, 0, w, h)
        self.date_overlay.setGeometry(0, 0, w, h)
        self.emotional_overlay.setGeometry(0, 0, w, h)

    # ----------------- TECLAS -----------------
    def keyPressEvent(self, e):
        if self.menu_mode and e.key() == Qt.Key_Space:
            print("\n[MENU] ESPAÇO PRESSIONADO - INICIANDO JOGO")
            self.menu_mode = False
            self.menu_overlay.hide()
            self.memories_container.show()
            
            # Para vídeo do menu
            self.video.stop()
            
            # Inicia game_logic
            self.game.start_game()
            
            # Mostra intro do prólogo (tela preta)
            self.start_phase_intro("2024 - 2025", "Um ano de momentos", "PROLOGO", "Assista")
            
        super().keyPressEvent(e)

    # ----------------- CAMERA -----------------
    def _show_cam(self, frame):
        if frame is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.cam_label.width(),
            self.cam_label.height(),
            Qt.KeepAspectRatio
        )
        self.cam_label.setPixmap(pix)

    # ===== VÍDEO TERMINOU =====
    def _on_video_finished(self):
        """Chamado quando vídeo (sem loop) termina"""
        print(f"[VIDEO] Vídeo terminou (fase {self.game.fase_atual})")
        fase_antes = self.game.fase_atual
        self.game.video_finished()
        print(f"[VIDEO] Game avançou para fase {self.game.fase_atual}")
        # Força re-detecção setando para fase anterior
        self.current_phase_displayed = fase_antes

    # ===== INTRO DE FASE =====
    def start_phase_intro(self, date_text, emotional_text, title_text, subtitle_text):
        """Inicia intro na tela preta"""
        if self.text_state != TextState.IDLE:
            print(f"[WARN] Intro bloqueada - estado: {self.text_state.value}")
            self.pending_intro = (date_text, emotional_text, title_text, subtitle_text)
            return
        
        print(f"[INTRO] Iniciando: {title_text}")
        
        # Esconde floating_text se estiver visível (ex: "COMPLETO!" ainda aparecendo)
        self.floating_text.hide()
        
        self._show_date(date_text, emotional_text, title_text, subtitle_text)

    def _show_date(self, date_text, emotional_text, title_text, subtitle_text):
        print(f"[1/4] Data: {date_text}")
        print(f"      → Próximo: Emocional '{emotional_text}'")
        print(f"      → Depois: Título '{title_text}' | Sub '{subtitle_text}'")
        self.text_state = TextState.SHOWING_DATE
        self.date_overlay.setText(date_text)
        self.date_overlay.show()
        self.date_overlay.raise_()
        
        effect = QGraphicsOpacityEffect(self.date_overlay)
        self.date_overlay.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(1000)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        QTimer.singleShot(2000, lambda: self._fade_out_date(emotional_text, title_text, subtitle_text))

    def _fade_out_date(self, emotional_text, title_text, subtitle_text):
        print("[1/4] → Fade out data...")
        effect = QGraphicsOpacityEffect(self.date_overlay)
        self.date_overlay.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(1000)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        QTimer.singleShot(1100, lambda: [
            self.date_overlay.hide(),
            self._show_emotional(emotional_text, title_text, subtitle_text)
        ])

    def _show_emotional(self, emotional_text, title_text, subtitle_text):
        print(f"[2/4] Emocional: {emotional_text}")
        self.text_state = TextState.SHOWING_EMOTIONAL
        self.emotional_overlay.setText(emotional_text)
        self.emotional_overlay.show()
        self.emotional_overlay.raise_()
        
        self.emotional_effect = QGraphicsOpacityEffect(self.emotional_overlay)
        self.emotional_overlay.setGraphicsEffect(self.emotional_effect)
        
        self.emotional_anim = QPropertyAnimation(self.emotional_effect, b"opacity")
        self.emotional_anim.setDuration(1000)
        self.emotional_anim.setStartValue(0)
        self.emotional_anim.setEndValue(1)
        self.emotional_anim.setEasingCurve(QEasingCurve.InOutSine)
        self.emotional_anim.start()
        
        QTimer.singleShot(2500, lambda: self._fade_out_emotional(title_text, subtitle_text))

    def _fade_out_emotional(self, title_text, subtitle_text):
        print("[2/4] → Fade out emocional...")
        effect = QGraphicsOpacityEffect(self.emotional_overlay)
        self.emotional_overlay.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(1000)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        QTimer.singleShot(1100, lambda: [
            self.emotional_overlay.hide(),
            self._show_title_center(title_text, subtitle_text)
        ])

    def _show_title_center(self, title_text, subtitle_text):
        print(f"[3/4] Título e subtítulo centralizados: {title_text} | {subtitle_text}")
        self.text_state = TextState.SHOWING_TITLE
        
        # Cria texto combinado com título maior e subtítulo menor
        combined_html = f"""
        <div style='text-align: center;'>
            <div style='font-size: 48px; font-weight: bold; color: #FFD700; margin-bottom: 20px;'>{title_text}</div>
            <div style='font-size: 28px; color: #FFCC66;'>{subtitle_text}</div>
        </div>
        """
        
        self.floating_text.setText(combined_html)
        self.floating_text.setTextFormat(Qt.RichText)
        self.floating_text.show()
        self.floating_text.raise_()
        
        effect = QGraphicsOpacityEffect(self.floating_text)
        self.floating_text.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(1000)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        QTimer.singleShot(2500, lambda: self._move_title_to_hud(title_text, subtitle_text))

    def _move_title_to_hud(self, title_text, subtitle_text):
        print("[3/4] → Título sobe pro HUD...")
        effect = QGraphicsOpacityEffect(self.floating_text)
        self.floating_text.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(600)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        def hide_and_reset():
            self.floating_text.hide()
            self.floating_text.setTextFormat(Qt.PlainText)  # Resetar para próximas vezes
        
        QTimer.singleShot(700, hide_and_reset)
        QTimer.singleShot(300, lambda: self._show_hud_fixed(title_text, subtitle_text))

    def _show_hud_fixed(self, title_text, subtitle_text):
        """HUD aparece e PERMANECE PARA SEMPRE até próximo vídeo"""
        print(f"[4/4] HUD: {title_text} | {subtitle_text}")
        self.text_state = TextState.SHOWING_HUD
        
        self.hud_title.setText(title_text)
        self.hud_subtitle.setText(subtitle_text)
        
        # Progresso: conta quantas fases REAIS já passaram
        real_phases = [1, 3, 5]
        if self.game.fase_atual in real_phases:
            current_real = real_phases.index(self.game.fase_atual) + 1
        else:
            current_real = sum(1 for p in real_phases if p < self.game.fase_atual)
        
        self.progress_label.setText(f"{current_real}/3")
        self.progress_label.adjustSize()
        self._update_positions()
        
        # CRÍTICO: Mostra HUD e mantém sempre no topo
        self.hud_bar.show()
        self.hud_bar.raise_()
        self.cam_label.raise_()
        
        # Remove qualquer GraphicsEffect antigo
        self.hud_bar.setGraphicsEffect(None)
        
        # Cria novo effect para fade in
        effect = QGraphicsOpacityEffect(self.hud_bar)
        self.hud_bar.setGraphicsEffect(effect)
        effect.setOpacity(0)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(1000)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        
        # Garante que _finish_intro seja chamado após animação
        QTimer.singleShot(1100, self._cleanup_hud_and_finish)

    def _cleanup_hud_and_finish(self):
        """Limpa efeitos do HUD e chama _finish_intro"""
        self.hud_bar.setGraphicsEffect(None)
        self.hud_bar.setStyleSheet("background-color: transparent;")
        print(f"[HUD] ✓ Visível e fixo!")
        print(f"      Título: '{self.hud_title.text()}'")
        print(f"      Subtítulo: '{self.hud_subtitle.text()}'")
        self._finish_intro()

    def _finish_intro(self):
        """Libera sistema e inicia vídeo/gameplay"""
        print("[✓] INTRO COMPLETA")
        self.text_state = TextState.IDLE
        
        # Se tem intro pendente na fila, executa
        if self.pending_intro:
            date, emo, title, sub = self.pending_intro
            self.pending_intro = None
            print(f"[QUEUE] Executando pendente: {title}")
            QTimer.singleShot(100, lambda: self.start_phase_intro(date, emo, title, sub))
            return
        
        # Se game_logic está esperando intro do prólogo terminar
        if self.game.waiting_for_intro_complete:
            print("[GAME] Notificando intro completa → iniciando prólogo")
            self.game.intro_completed()
            # Força detecção da fase 0 (prólogo) setando current_phase diferente
            self.current_phase_displayed = -1
            print(f"[GAME] Fase agora é {self.game.fase_atual}, current_phase={self.current_phase_displayed}")
            return
        
        # Fases normais: inicia loop do corte
        if self.game.fase_atual >= 0 and self.game.fase_atual < len(self.game.fases):
            fase = self.game.fases[self.game.fase_atual]
            if fase["tipo"] != "video" and "loop_file" in fase:
                print(f"[VIDEO] Loop do corte: {fase['loop_file']}")
                self.video.play_file(fase["loop_file"], loop=True)

    # ----------------- FLOATING TEXT -----------------
    def show_floating_text(self, text, duration=2000):
        if self.text_state != TextState.IDLE:
            print(f"[WARN] Floating bloqueado")
            return
        
        print(f"[FLOATING] {text}")
        self.floating_text.setText(text)
        self.floating_text.show()
        self.floating_text.raise_()

        effect = QGraphicsOpacityEffect(self.floating_text)
        self.floating_text.setGraphicsEffect(effect)
        effect.setOpacity(0)

        anim_in = QPropertyAnimation(effect, b"opacity")
        anim_in.setDuration(800)
        anim_in.setStartValue(0)
        anim_in.setEndValue(1)
        anim_in.setEasingCurve(QEasingCurve.InOutSine)
        anim_in.start(QPropertyAnimation.DeleteWhenStopped)

        QTimer.singleShot(duration, lambda: self._floating_fade_out(effect))
    
    def _floating_fade_out(self, old_effect):
        effect = QGraphicsOpacityEffect(self.floating_text)
        self.floating_text.setGraphicsEffect(effect)
        effect.setOpacity(1)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(800)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InOutSine)
        anim.finished.connect(self.floating_text.hide)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    # ----------------- MEMÓRIA -----------------
    def unlock_memory(self, index):
        if index < len(self.memory_cards):
            self.memory_cards[index].unlock()
            unlocked = sum(1 for card in self.memory_cards if not card.locked)
            self.memories_count.setText(f"{unlocked}/3")

    # ----------------- UPDATE STATE -----------------
    def update_state(self, game, dados, cam_frame, evento):
        self._show_cam(cam_frame)
        
        # Log se recebeu evento
        if evento:
            print(f"[UPDATE_STATE] Evento recebido: '{evento}'")
        
        # Debug
        if game.fase_atual == 0 and self.current_phase_displayed != 0:
            print(f"[DEBUG UPDATE] fase_atual={game.fase_atual}, current={self.current_phase_displayed}, menu={self.menu_mode}, waiting={game.waiting_for_intro_complete}")
        
        # Ignora durante menu ou intro
        if self.menu_mode or game.waiting_for_intro_complete:
            return
        
        # Jogo terminou
        if game.fase_atual >= len(game.fases):
            if self.current_phase_displayed != "FIM":
                print("\n[JOGO] FINALIZADO!")
                self.current_phase_displayed = "FIM"
            return

        # PRIMEIRO: Processa evento de fase concluída (antes de detectar mudança)
        if evento == "fase_ok":
            # A fase que foi completada é a anterior (game já incrementou fase_atual)
            fase_completada = game.fase_atual - 1
            
            # Evita processar o mesmo evento múltiplas vezes
            if self.shown_complete_for_phase != fase_completada:
                print(f"[EVENTO] Fase {fase_completada} OK! (agora em fase {game.fase_atual})")
                self.shown_complete_for_phase = fase_completada
                
                # Para o loop antes de avançar para o vídeo da fase
                self.video.stop()
                
                # Desbloqueia memória apenas nas FASES REAIS (1, 3, 5)
                if fase_completada in [1, 3, 5]:
                    memory_index = {1: 0, 3: 1, 5: 2}[fase_completada]
                    print(f"[MEMORIA] ✓ Desbloqueando cartinha {memory_index} (completou fase {fase_completada})")
                    self.unlock_memory(memory_index)
                else:
                    print(f"[MEMORIA] Fase {fase_completada} não desbloqueia memória (não é fase real)")
                
                self.show_floating_text("COMPLETO!", 2500)
                
                # NÃO atualiza current_phase_displayed aqui!
                # Deixa para o bloco de detecção de mudança de fase fazer isso
                # e iniciar o vídeo/intro da próxima fase

        # DEPOIS: Detecta mudança de fase (verifica se é diferente E se fase >= 0)
        if self.current_phase_displayed != game.fase_atual and game.fase_atual >= 0:
            fase = game.fases[game.fase_atual]
            print(f"\n[FASE] {self.current_phase_displayed} → {game.fase_atual} ({fase['tipo']}) '{fase.get('nome', '?')}'")
            
            self.shown_complete_for_phase = -1
            
            if fase["tipo"] == "video":
                print(f"[FASE] Iniciando vídeo: {fase['arquivo']}")
                # Para qualquer vídeo anterior
                self.video.stop()
                # Toca vídeo completo (sem loop)
                self.video.play_file(fase["arquivo"], loop=False)
                self.current_phase_displayed = game.fase_atual
                return
            
            # FASES REAIS - mostra intro (tela preta) e PARA vídeo
            # Mapeamento correto conforme app_qt.py:
            # 0: vídeo prólogo
            # 1: gesto_duplo (A+B) - "alianca" ← FASE REAL
            # 2: vídeo fase_1
            # 3: objeto (cat) - "boo" ← FASE REAL
            # 4: vídeo fase_2
            # 5: gesto_unico (A) - "estadio" ← FASE REAL
            # 6: vídeo fase_3
            
            real_phases = {
                1: {
                    "date": "05 de Julho de 2025",
                    "emotional": "Me Mostra Sua Aliança ✋👈",
                    "title": "ALIANCA",
                    "subtitle": "Gestos: A + B",
                    "loop_file": "assets/ney1.mp4"  # ⚠️ Mude para loop da fase
                },
                3: {
                    "date": "13 de Novembro de 2025",
                    "emotional": "Me Mostra a Gata 🐈‍⬛",
                    "title": "BOO",
                    "subtitle": "Mostre: cat",
                    "loop_file": "assets/ney2.mp4"  # ⚠️ Mude para loop da fase
                },
                5: {
                    "date": "05 de Abril de 2025",
                    "emotional": "Grande Final",
                    "title": "ESTADIO",
                    "subtitle": "Gesto: A",
                    "loop_file": "assets/prolog.mp4"  # ⚠️ Mude para loop da fase
                }
            }
            
            if game.fase_atual in real_phases:
                data = real_phases[game.fase_atual]
                print(f"[FASE] Para vídeo e mostra intro para fase {game.fase_atual}")
                
                # Para vídeo antes de mostrar intro
                self.video.stop()
                
                # Guarda arquivo de loop para iniciar depois
                fase["loop_file"] = data["loop_file"]
                
                # Inicia intro (tela preta → loop depois)
                self.start_phase_intro(
                    data["date"],
                    data["emotional"],
                    data["title"],
                    data["subtitle"]
                )
            
            self.current_phase_displayed = game.fase_atual