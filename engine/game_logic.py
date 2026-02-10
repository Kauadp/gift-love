import time

class GameState:
    def __init__(self, fases):
        self.fases = fases
        self.fase_atual = -1  # -1 = menu
        self.cooldown_time = 0
        self.menu_active = True
        self.waiting_for_intro_complete = False

    def start_game(self):
        """Chamado quando usuário aperta ESPAÇO no menu"""
        print("[GAME] Jogo iniciado - aguardando intro...")
        self.menu_active = False
        self.waiting_for_intro_complete = True
        # Fase ainda é -1 (menu), UI vai mostrar textos de intro

    def intro_completed(self):
        """Chamado quando textos de intro terminam"""
        print("[GAME] Intro completa - iniciando prólogo (fase 0)")
        self.waiting_for_intro_complete = False
        self.fase_atual = 0  # Prólogo
        self.cooldown_time = time.time() + 0.5

    def video_finished(self):
        """Chamado quando vídeo (prólogo ou fase) termina"""
        print(f"[GAME] Vídeo terminou na fase {self.fase_atual}")
        if self.fase_atual >= 0 and self.fase_atual < len(self.fases):
            fase = self.fases[self.fase_atual]
            if fase["tipo"] == "video":
                # Avança para próxima fase
                self.fase_atual += 1
                self.cooldown_time = time.time() + 0.5
                print(f"[GAME] → Avançando para fase {self.fase_atual}")

    def update(self, g0, g1, objetos=None):
        """Verifica condições de vitória em fases de gameplay"""
        if self.menu_active or self.waiting_for_intro_complete:
            return None

        if time.time() < self.cooldown_time:
            return None

        if self.fase_atual >= len(self.fases):
            return None

        fase = self.fases[self.fase_atual]
        tipo = fase["tipo"]

        # Fases de vídeo não são verificadas aqui
        if tipo == "video":
            return None

        # Debug: mostra o que está sendo verificado
        if g0 != "Nenhum" or g1 != "Nenhum" or (objetos and len(objetos) > 0):
            print(f"[GAME DEBUG] Fase {self.fase_atual} ({tipo}): g0={g0}, g1={g1}, obj={objetos}")

        # Gestos/objetos
        if tipo == "gesto_unico":
            if g0 == fase["gesto"] or g1 == fase["gesto"]:
                print(f"[GAME] ✓ Gesto {fase['gesto']} detectado!")
                self.fase_atual += 1
                self.cooldown_time = time.time() + 1.0
                return "fase_ok"

        if tipo == "gesto_duplo":
            a, b = fase["gestos"]
            print(f"[GAME DEBUG] Verificando gesto_duplo: precisa {a}+{b}, tem g0={g0}, g1={g1}")
            if (g0 == a and g1 == b) or (g0 == b and g1 == a):
                print(f"[GAME] ✓ Gesto duplo {a}+{b} detectado!")
                self.fase_atual += 1
                self.cooldown_time = time.time() + 1.0
                return "fase_ok"

        if tipo == "objeto":
            if objetos and fase["objeto"] in objetos:
                print(f"[GAME] ✓ Objeto {fase['objeto']} detectado!")
                self.fase_atual += 1
                self.cooldown_time = time.time() + 1.0
                return "fase_ok"

        return None