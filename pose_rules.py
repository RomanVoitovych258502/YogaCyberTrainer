import math

AVAILABLE_POSES = [
    "pies_z_glowa_w_dol",
    "pozycja_dziecka",
    "pozycja_drzewa",
    "pozycja_gory"
]

# Indeksy punktów konstrukcji ciała
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28


def hint(voice_text: str, gui_text: str):
    return [voice_text, gui_text]


def calculate_angle(a, b, c):
    ang = math.degrees(
        math.atan2(c.y - b.y, c.x - b.x) -
        math.atan2(a.y - b.y, a.x - b.x)
    )
    return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)


def check_cam2_rules(target_pose, lm2):
    """
    Dodatkowe reguły z perspektywy kamery 2.
    Zwraca listę par: [tekst_dla_voice, tekst_dla_GUI].
    """
    if lm2 is None:
        return []

    hints2 = []

    if target_pose == "pozycja_gory":
        if abs(lm2[L_ANKLE].x - lm2[R_ANKLE].x) > 0.10:
            hints2.append(hint("Złącz stopy", "Zlacz stopy"))
        if abs(lm2[L_KNEE].x - lm2[R_KNEE].x) > 0.12:
            hints2.append(hint("Złącz kolana", "Zlacz kolana"))

    elif target_pose == "pozycja_drzewa":
        mean_hip_x = (lm2[L_HIP].x + lm2[R_HIP].x) / 2
        mean_sh_x = (lm2[L_SHOULDER].x + lm2[R_SHOULDER].x) / 2

        if abs(mean_sh_x - mean_hip_x) > 0.07:
            hints2.append(hint("Wyprostuj plecy", "Wyprostuj plecy"))

        if abs(lm2[NOSE].x - mean_hip_x) > 0.09:
            hints2.append(hint("Wyprostuj głowę", "Wyprostuj glowe"))

    return hints2


def check_pose_rules(target_pose, lm1, lm2=None, dual_camera_enabled=False):
    """
    Zwraca:
        (detected_pose, lista_podpowiedzi)

    lista_podpowiedzi ma format:
        [ ["voice text", "gui text"], ... ]
    """
    if not lm1:
        return "?", []

    # Kąty
    l_hip_ang = calculate_angle(lm1[L_SHOULDER], lm1[L_HIP], lm1[L_KNEE])
    r_hip_ang = calculate_angle(lm1[R_SHOULDER], lm1[R_HIP], lm1[R_KNEE])
    l_knee_ang = calculate_angle(lm1[L_HIP], lm1[L_KNEE], lm1[L_ANKLE])
    r_knee_ang = calculate_angle(lm1[R_HIP], lm1[R_KNEE], lm1[R_ANKLE])
    l_elbow_ang = calculate_angle(lm1[L_SHOULDER], lm1[L_ELBOW], lm1[L_WRIST])
    r_elbow_ang = calculate_angle(lm1[R_SHOULDER], lm1[R_ELBOW], lm1[R_WRIST])
    l_sh_ang = calculate_angle(lm1[L_HIP], lm1[L_SHOULDER], lm1[L_WRIST])
    r_sh_ang = calculate_angle(lm1[R_HIP], lm1[R_SHOULDER], lm1[R_WRIST])

    # Średnie współrzędne
    mean_hip_y = (lm1[L_HIP].y + lm1[R_HIP].y) / 2
    mean_sh_y = (lm1[L_SHOULDER].y + lm1[R_SHOULDER].y) / 2
    mean_ank_y = (lm1[L_ANKLE].y + lm1[R_ANKLE].y) / 2
    mean_wrist_y = (lm1[L_WRIST].y + lm1[R_WRIST].y) / 2
    mean_wrist_x = (lm1[L_WRIST].x + lm1[R_WRIST].x) / 2
    mean_sh_x = (lm1[L_SHOULDER].x + lm1[R_SHOULDER].x) / 2
    mean_hip_x = (lm1[L_HIP].x + lm1[R_HIP].x) / 2
    nose_y = lm1[NOSE].y
    nose_x = lm1[NOSE].x

    hints = []

    if target_pose == "pies_z_glowa_w_dol":
        if not (mean_wrist_y > mean_sh_y):
            hints.append(hint("Oprzyj dłonie", "Oprzyj dlonie"))
        if not (l_hip_ang < 120 and r_hip_ang < 120):
            hints.append(hint("Ugnij mocniej biodra", "Ugnij mocniej biodra"))
        if not (mean_hip_y < mean_sh_y):
            hints.append(hint("Unieś biodra wyżej", "Unies biodra wyzej"))
        if not (l_knee_ang > 140 and r_knee_ang > 140):
            hints.append(hint("Wyprostuj kolana", "Wyprostuj kolana"))
        if not (l_elbow_ang > 140 and r_elbow_ang > 140):
            hints.append(hint("Wyprostuj łokcie", "Wyprostuj lokcie"))

    elif target_pose == "pozycja_dziecka":
        if not (l_knee_ang < 80 and r_knee_ang < 80):
            hints.append(hint("Ugnij kolana bardziej", "Ugnij kolana bardziej"))
        if not (abs(mean_hip_y - mean_ank_y) < 0.10):
            hints.append(hint("Oprzyj biodra na piętach", "Oprzyj biodra na pietach"))
        if not (mean_sh_y > mean_hip_y - 0.05):
            hints.append(hint("Opuść tors niżej", "Opusc tors nizej"))
        if not ((l_sh_ang > 145 and r_sh_ang > 145) and (l_elbow_ang > 130 and r_elbow_ang > 130)):
            hints.append(hint("Wyciągnij ręce do przodu", "Wyciagnij rece do przodu"))

    elif target_pose == "pozycja_drzewa":
        tree_l = (l_knee_ang < 110 and r_knee_ang > 150) and (lm1[L_ANKLE].y < lm1[R_KNEE].y + 0.05)
        tree_r = (r_knee_ang < 110 and l_knee_ang > 150) and (lm1[R_ANKLE].y < lm1[L_KNEE].y + 0.05)

        if not (tree_l or tree_r):
            hints.append(hint("Postaw stopę na łydce", "Postaw stope na lydce"))
        if abs(mean_sh_x - mean_hip_x) > 0.04:
            hints.append(hint("Nie przechylaj tułowia na boki", "Nie przechylaj tulowia na boki"))
        if abs(nose_x - mean_hip_x) > 0.05:
            hints.append(hint("Trzymaj głowę prosto w osi ciała", "Trzymaj glowe prosto w osi ciala"))
        if not (mean_wrist_y < nose_y):
            hints.append(hint("Unieś dłonie nad głowę", "Unies dlonie nad glowe"))
        if not (abs(lm1[L_WRIST].x - lm1[R_WRIST].x) < 0.15):
            hints.append(hint("Złącz dłonie razem", "Zlacz dlonie razem"))
        if abs(mean_wrist_x - mean_hip_x) > 0.06:
            hints.append(hint("Wycentruj dłonie nad głową", "Wycentruj dlonie nad glowa"))
        if not (l_elbow_ang < 155 and r_elbow_ang < 155):
            hints.append(hint("Ugnij lekko łokcie", "Ugnij lekko lokcie"))
        if not (abs(lm1[L_ELBOW].x - lm1[R_ELBOW].x) > abs(lm1[L_SHOULDER].x - lm1[R_SHOULDER].x)):
            hints.append(hint("Rozstaw łokcie szerzej", "Rozstaw lokcie szerzej"))

    elif target_pose == "pozycja_gory":
        if not (abs(lm1[L_ANKLE].x - lm1[R_ANKLE].x) < 0.18):
            hints.append(hint("Złącz stopy razem", "Zlacz stopy razem"))
        if not ((l_knee_ang > 145 and r_knee_ang > 145) and (l_hip_ang > 140 and r_hip_ang > 140)):
            hints.append(hint("Wyprostuj nogi i biodra", "Wyprostuj nogi i biodra"))
        if not (mean_wrist_y < nose_y):
            hints.append(hint("Unieś ręce", "Unies rece"))
        if not (abs(mean_wrist_x - nose_x) > 0.08):
            hints.append(hint("Odchyl ręce do tyłu", "Odchyl rece do tylu"))
        if not (abs(mean_sh_x - mean_hip_x) > 0.05):
            hints.append(hint("Wygnij lekko plecy", "Wygnij lekko plecy"))

    # Kamera 2
    if dual_camera_enabled and lm2 is not None:
        hints.extend(check_cam2_rules(target_pose, lm2))

    if len(hints) > 0:
        return "?", hints

    return target_pose, []