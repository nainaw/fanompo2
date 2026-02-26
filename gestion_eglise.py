import csv
import datetime
import os
import random
import subprocess
from collections import defaultdict

# --- CONFIGURATION ---
FICHIERS = {
    'membres': ('membres.csv', ['id', 'nom', 'quota_max', 'groupe']),
    'taches': ('taches.csv', ['id', 'nom_tache', 'rang', 'description']),
    'competences': ('competences.csv', ['membre_id', 'tache_id']),
    'planning': ('planning.csv', ['date', 'tache_id', 'membre_id', 'membre_nom', 'tache_nom', 'tache_desc'])
}

ID_ROLE_ANCIEN = "100" 
ID_ROLE_JA = "101"
TACHES_GROUPES = ['SSM', 'SST', 'SS5']

# --- OUTILS DE BASE ---

def lire_csv(nom):
    chemin = FICHIERS[nom][0]
    if not os.path.exists(chemin): return []
    with open(chemin, mode='r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def ecrire_csv(nom, donnees):
    chemin, headers = FICHIERS[nom]
    with open(chemin, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(donnees)
    print(f"✅ {chemin} mis à jour.")

def initialiser_fichiers():
    for f, (chemin, headers) in FICHIERS.items():
        if not os.path.exists(chemin):
            with open(chemin, 'w', newline='', encoding='utf-8') as file:
                csv.DictWriter(file, fieldnames=headers).writeheader()

# --- GESTION DES TACHES (CRUD) ---

def menu_taches():
    while True:
        print("\n--- GESTION DES TÂCHES ---")
        print("1.Voir | 2.Ajouter | 3.Supprimer | 0.Retour")
        choix = input("Choix : ")
        if choix == '1':
            lister_taches()
        elif choix == '2':
            nom = input("Nom de la tâche (ex: CUM) : ")
            desc = input("Description (ex: Mitarika) : ")
            rang = input("Rang d'affichage (1-20) : ")
            tlist = lire_csv('taches')
            nid = str(max([int(t['id']) for t in tlist] + [0]) + 1)
            tlist.append({'id': nid, 'nom_tache': nom, 'rang': rang, 'description': desc})
            ecrire_csv('taches', tlist)
        elif choix == '3':
            lister_taches()
            tid = input("ID de la tâche à supprimer définitivement : ")
            if tid:
                ecrire_csv('taches', [t for t in lire_csv('taches') if t['id'] != tid])
                # Cascade : on enlève cette compétence à tout le monde
                ecrire_csv('competences', [c for c in lire_csv('competences') if c['tache_id'] != tid])
        elif choix == '0': break

# --- GESTION DES COMPETENCES ---

def modifier_competences_membre(mid):
    taches_ref = {t['id']: t['nom_tache'] for t in lire_csv('taches')}
    membres_ref = {m['id']: m['nom'] for m in lire_csv('membres')}
    
    if mid not in membres_ref:
        print("❌ ID Membre inconnu.")
        return

    # Affichage des compétences actuelles
    actuelles = [c['tache_id'] for c in lire_csv('competences') if c['membre_id'] == mid]
    noms = [f"{tid}:{taches_ref.get(tid, 'Unknown')}" for tid in actuelles]
    
    print(f"\n--- COMPETENCES DE : {membres_ref[mid].upper()} ---")
    print(f"Possède déjà : {', '.join(noms) if noms else 'Rien'}")
    
    lister_taches()
    print("\nActions possibles :")
    print("- Entrez les IDs séparés par virgule (ex: 1,4,100) pour REPLACER la liste")
    print("- Tapez 'sup' pour EFFACER TOUTES les compétences de ce membre")
    print("- Entrée pour ne rien changer")
    
    saisie = input("\nVotre choix : ").strip().lower()
    if not saisie: return
    
    clist = [c for c in lire_csv('competences') if c['membre_id'] != mid]
    
    if saisie != 'sup':
        valides = [i.strip() for i in saisie.split(',') if i.strip() in taches_ref]
        for v in valides:
            clist.append({'membre_id': mid, 'tache_id': v})
        if not valides: print("⚠️ Aucune ID valide saisie."); return

    ecrire_csv('competences', clist)

# --- GENERATION HTML (Planning + Dashboard) ---

def generer_fichiers_html():
    plan = lire_csv('planning')
    membres = lire_csv('membres')
    taches = sorted(lire_csv('taches'), key=lambda x: int(x['rang'] or 99))
    if not plan: return

    # 1. PLANNING.HTML (3 dates futures)
    auj = str(datetime.date.today())
    dates_f = sorted(list(set(p['date'] for p in plan if p['date'] >= auj)))[:3]
    par_date = defaultdict(dict)
    for p in plan: 
        if p['date'] in dates_f: par_date[p['date']][p['tache_id']] = p['membre_nom']

    html = "<html><head><meta charset='UTF-8'><style>body{font-family:sans-serif;padding:20px;}table{border-collapse:collapse;width:100%;}th,td{border:1px solid #aaa;padding:8px;}th{background:#2c3e50;color:white;text-align:center;}</style></head><body>"
    html += "<h2>📅 Prochains Services</h2><table><tr><th>Tâche</th>"
    for d in dates_f: html += f"<th>{d}</th>"
    html += "</tr>"
    for t in taches:
        if t['id'] in [ID_ROLE_ANCIEN, ID_ROLE_JA]: continue
        html += f"<tr><td><b>{t.get('description', t['nom_tache'])}</b></td>"
        for d in dates_f: html += f"<td align='center'>{par_date[d].get(t['id'], '-')}</td>"
        html += "</tr>"
    html += "</table></body></html>"
    with open("planning.html", "w", encoding="utf-8") as f: f.write(html)

    # 2. DASHBOARD.HTML
    stats = defaultdict(lambda: defaultdict(str))
    count = defaultdict(int)
    for p in plan:
        stats[p['membre_id']][p['tache_id']] = p['date']
        if p['membre_id'] not in ["GROUPE", "VISITEUR"]: count[p['membre_id']] += 1
    
    html_d = "<html><head><meta charset='UTF-8'><style>body{font-family:sans-serif;font-size:12px;}table{border-collapse:collapse;width:100%;}.name-col{background:#eee;font-weight:bold;position:sticky;left:0;}th{background:#34495e;color:white;}td,th{border:1px solid #ccc;padding:4px;text-align:center;}</style></head><body>"
    html_d += "<h2>📊 Historique & Quotas</h2><table><tr><th class='name-col'>Membre (Total)</th>"
    for t in taches: 
        if t['id'] not in [ID_ROLE_ANCIEN, ID_ROLE_JA]: html_d += f"<th>{t['nom_tache']}</th>"
    html_d += "</tr>"
    for m in membres:
        html_d += f"<tr><td class='name-col'>{m['nom']} ({count[m['id']]}/{m['quota_max']})</td>"
        for t in taches:
            if t['id'] in [ID_ROLE_ANCIEN, ID_ROLE_JA]: continue
            d_last = stats[m['id']].get(t['id'], '-')
            html_d += f"<td>{d_last}</td>"
        html_d += "</tr>"
    html_d += "</table></body></html>"
    with open("dashboard.html", "w", encoding="utf-8") as f: f.write(html_d)
    print("🌐 planning.html et dashboard.html mis à jour.")

# --- LOGIQUE DE GENERATION ---

def generer_planning():
    membres_l = lire_csv('membres')
    taches_l = lire_csv('taches')
    hist_l = lire_csv('planning')
    comps_l = lire_csv('competences')
    m_dict = {m['id']: m['nom'] for m in membres_l}

    date_defaut = datetime.date.today()
    if hist_l:
        try: date_defaut = datetime.datetime.strptime(hist_l[-1]['date'], "%Y-%m-%d").date() + datetime.timedelta(days=7)
        except: pass
    while date_defaut.weekday() != 5: date_defaut += datetime.timedelta(days=1)
    
    inp = input(f"Date de service [{date_defaut}] ou 0 pour annuler : ")
    if inp == '0': return
    try:
        date_cur = datetime.datetime.strptime(inp, "%Y-%m-%d").date() if inp else date_defaut
    except: print("❌ Format date invalide."); return

    c_par_t = defaultdict(list)
    for c in comps_l: c_par_t[c['tache_id']].append(c['membre_id'])
    for m in membres_l: # Synchro Groupes
        if m['groupe'] == 'ANCIEN': c_par_t[ID_ROLE_ANCIEN].append(m['id'])
        if m['groupe'] == 'JA': c_par_t[ID_ROLE_JA].append(m['id'])

    stats_p = defaultdict(int); last_g = defaultdict(lambda: datetime.date(2000,1,1))
    for p in hist_l:
        stats_p[p['membre_id']] += 1
        d = datetime.datetime.strptime(p['date'], "%Y-%m-%d").date()
        if d > last_g[p['membre_id']]: last_g[p['membre_id']] = d

    dispo_j = set(); resultat_jour = []
    num_samedi = (date_cur.day - 1) // 7 + 1
    est_trim = date_cur.month in [1, 4, 7, 10]
    est_5eme = num_samedi == 5

    for t in sorted(taches_l, key=lambda x: int(x['rang'] or 99)):
        if t['id'] in [ID_ROLE_ANCIEN, ID_ROLE_JA]: continue
        fid, fnom = "999", "À DÉTERMINER"
        
        if t['nom_tache'].upper() in TACHES_GROUPES:
            mapping = {1: "TANORA ZOKINY", 2: "ZATOVO", 3: "LEHIBE I", 4: "LEHIBE II"}
            fnom = mapping.get(num_samedi, "GROUPE"); fid = "GROUPE"
        elif est_5eme and t['nom_tache'].upper().startswith('CU'):
            fid, fnom = "GROUPE", "MINENF"
        else:
            candidates = list(set(c_par_t[t['id']]))
            if t['nom_tache'].upper() == 'CUTL' and est_trim and num_samedi <= 2: candidates = c_par_t[ID_ROLE_ANCIEN]
            elif num_samedi == 3 and t['nom_tache'].upper().startswith('CU'): candidates = c_par_t[ID_ROLE_JA]
            
            scores = []
            for mid in candidates:
                if mid in dispo_j: continue
                m_data = next((m for m in membres_l if m['id'] == mid), None)
                if not m_data or int(m_data['quota_max']) == 0: continue
                if stats_p[mid] >= int(m_data['quota_max']): continue
                
                repos = (date_cur - last_g[mid]).days // 7
                score = (repos * 1000) - (stats_p[mid] * 5000) + random.randint(0, 500)
                scores.append({'id': mid, 'score': score})
            
            if scores:
                choisi = max(scores, key=lambda x: x['score'])['id']
                fid, fnom = choisi, m_dict[choisi]; dispo_j.add(choisi)
        
        resultat_jour.append({
            'date': str(date_cur), 'tache_id': t['id'], 'membre_id': fid, 
            'membre_nom': fnom, 'tache_nom': t['nom_tache'], 
            'tache_desc': t.get('description', t['nom_tache'])
        })

    ecrire_csv('planning', hist_l + resultat_jour)
    generer_fichiers_html()

# --- MODIFICATION PLANNING ---

def modifier_planning():
    plan = lire_csv('planning')
    if not plan: return
    dates = sorted(list(set(p['date'] for p in plan)), reverse=True)[:5]
    print("\n--- MODIFIER UN SERVICE EXISTANT ---")
    for i, d in enumerate(dates): print(f"{i}. {d}")
    sel = input("Choisir date (index) : ")
    if not sel.isdigit(): return
    date_sel = dates[int(sel)]
    
    lignes = [p for p in plan if p['date'] == date_sel]
    for i, l in enumerate(lignes): print(f"{i}. {l['tache_nom']} : {l['membre_nom']}")
    
    idx = input("N° de ligne à changer : ")
    if not idx.isdigit(): return
    
    print("1. Remplacer par un membre | 2. Noter un visiteur externe")
    mode = input("Choix : ")
    if mode == '1':
        lister_membres()
        mid = input("ID du nouveau membre : ")
        m_ref = {m['id']: m['nom'] for m in lire_csv('membres')}
        if mid in m_ref:
            lignes[int(idx)]['membre_id'] = mid
            lignes[int(idx)]['membre_nom'] = m_ref[mid]
    else:
        lignes[int(idx)]['membre_nom'] = input("Nom du visiteur : ")
        lignes[int(idx)]['membre_id'] = "VISITEUR"
    
    # Reconstruction du fichier
    reste = [p for p in plan if p['date'] != date_sel]
    ecrire_csv('planning', reste + lignes)
    generer_fichiers_html()

# --- MAIN ---

def lister_taches():
    t_list = sorted(lire_csv('taches'), key=lambda x: int(x['rang'] or 99))
    print("\n--- RÉFÉRENTIEL TACHES ---")
    for t in t_list: print(f"ID {t['id']}: {t['nom_tache']} ({t.get('description','')})")

def lister_membres():
    m_list = lire_csv('membres')
    print("\n--- RÉFÉRENTIEL MEMBRES ---")
    for m in m_list: print(f"ID {m['id']}: {m['nom']:<20} | GRP: {m['groupe']}")

def main():
    initialiser_fichiers()
    while True:
        print("\n===== MENU PRINCIPAL =====")
        print("1. Membres | 2. Tâches | 3. Compétences | 4. GENERER | 5. MODIFIER | 0. Quitter")
        c = input("Choix : ")
        if c == '1':
            print("\n1.Voir | 2.Ajouter | 3.Supprimer | 0.Retour")
            m_c = input("Choix : ")
            if m_c == '1': lister_membres()
            elif m_c == '2': # Ajout rapide
                nom = input("Nom : "); g = input("Groupe (ANCIEN/JA/STANDART) : "); q = input("Quota : ")
                mlist = lire_csv('membres')
                nid = str(max([int(m['id']) for m in mlist] + [0]) + 1)
                mlist.append({'id': nid, 'nom': nom, 'quota_max': q, 'groupe': g})
                ecrire_csv('membres', mlist)
                modifier_competences_membre(nid)
            elif m_c == '3':
                lister_membres(); tid = input("ID à supprimer : ")
                if tid:
                    ecrire_csv('membres', [m for m in lire_csv('membres') if m['id'] != tid])
                    ecrire_csv('competences', [cp for cp in lire_csv('competences') if cp['membre_id'] != tid])
        elif c == '2': menu_taches()
        elif c == '3':
            lister_membres(); mid = input("ID Membre pour gérer ses compétences : ")
            if mid: modifier_competences_membre(mid)
        elif c == '4': 
            generer_planning()
            generer_fichiers_html()
            
            # --- PUBLICATION AUTOMATIQUE ---
            print("\n🚀 Publication sur GitHub en cours...")
            try:
                # Calcul du chemin exact du script shell
                import os
                chemin_script = os.path.join(os.path.dirname(__file__), "publier.sh")
                
                # Exécution
                subprocess.run([chemin_script], check=True)
            except FileNotFoundError:
                print("⚠️ Erreur : Le fichier 'publier.sh' est introuvable dans le dossier du script.")
            except Exception as e:
                print(f"⚠️ Erreur système lors de la publication : {e}")        
        elif c == '5': modifier_planning()
        elif c == '0': break

if __name__ == "__main__":
    main()