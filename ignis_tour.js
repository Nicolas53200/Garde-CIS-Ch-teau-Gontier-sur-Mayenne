/* ═══════════════════════════════════════════════════════════════
   IGNIS NOVA — Tour guidé & FAQ
   Fichier autonome injecté dans chaque interface CIS.
   Crée un bouton flottant en bas à droite avec deux modes :
     1. Visite guidée pas-à-pas (coach marks)
     2. Questions fréquentes
   ═══════════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  // ─────────────────────────────────────────────────────────────
  // Empêcher la double-initialisation
  // ─────────────────────────────────────────────────────────────
  if (window.__IGNIS_TOUR_LOADED__) return;
  window.__IGNIS_TOUR_LOADED__ = true;

  // ─────────────────────────────────────────────────────────────
  // CSS injecté
  // ─────────────────────────────────────────────────────────────
  var css = `
  /* Bouton flottant */
  #ignis-help-btn {
    position: fixed;
    bottom: 16px;
    right: 16px;
    width: 52px; height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f59e0b 0%, #dc2626 100%);
    color: #fff;
    font-size: 24px;
    font-weight: 900;
    border: none;
    cursor: pointer;
    box-shadow: 0 6px 20px rgba(220,38,38,0.4), 0 2px 6px rgba(0,0,0,0.3);
    z-index: 999990;
    display: flex; align-items: center; justify-content: center;
    transition: all .2s ease;
    font-family: 'Source Sans Pro', sans-serif;
  }
  #ignis-help-btn:hover {
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 8px 28px rgba(220,38,38,0.5), 0 3px 10px rgba(0,0,0,0.4);
  }
  #ignis-help-btn::before { content: '?'; }

  /* Menu principal (choix entre tour/FAQ) */
  .ignis-modal-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,.78);
    backdrop-filter: blur(4px);
    z-index: 999991;
    display: flex; align-items: center; justify-content: center;
    animation: ignisFadeIn .2s ease;
  }
  @keyframes ignisFadeIn { from { opacity: 0 } to { opacity: 1 } }

  .ignis-modal-box {
    background: #0d1b2e;
    border: 1px solid rgba(245,158,11,.3);
    border-radius: 18px;
    padding: 28px;
    width: 560px;
    max-width: 92vw;
    max-height: 88vh;
    overflow-y: auto;
    color: #fff;
    font-family: 'Source Sans Pro', sans-serif;
    box-shadow: 0 20px 60px rgba(0,0,0,.5);
    animation: ignisSlideUp .25s ease;
  }
  @keyframes ignisSlideUp { from {transform:translateY(20px);opacity:0} to {transform:translateY(0);opacity:1} }

  .ignis-modal-title {
    font-size: 20px; font-weight: 800;
    color: #f59e0b;
    margin-bottom: 6px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .ignis-modal-subtitle {
    font-size: 13px; color: #94a3b8;
    margin-bottom: 22px;
  }
  .ignis-modal-close {
    background: none; border: none;
    color: #64748b; font-size: 24px;
    cursor: pointer; padding: 0; line-height: 1;
    transition: color .15s;
  }
  .ignis-modal-close:hover { color: #ef4444; }

  /* Tuiles menu */
  .ignis-tile-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
    margin-top: 6px;
  }
  .ignis-tile-grid-3 {
    grid-template-columns: 1fr 1fr 1fr;
  }
  @media (max-width: 600px) {
    .ignis-tile-grid, .ignis-tile-grid-3 { grid-template-columns: 1fr; }
  }
  .ignis-tile {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 14px;
    padding: 22px 14px;
    text-align: center;
    cursor: pointer;
    transition: all .2s;
  }
  .ignis-tile:hover {
    background: rgba(245,158,11,.1);
    border-color: rgba(245,158,11,.4);
    transform: translateY(-2px);
  }
  .ignis-tile-icon { font-size: 38px; margin-bottom: 10px; }
  .ignis-tile-name { font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 4px; }
  .ignis-tile-sub { font-size: 11.5px; color: #94a3b8; line-height: 1.4; }

  /* Feedback form */
  .ignis-fb-group { margin-bottom: 14px; }
  .ignis-fb-label {
    display: block;
    color: #94a3b8; font-size: 11px; font-weight: 700;
    letter-spacing: .8px; text-transform: uppercase;
    margin-bottom: 6px;
  }
  .ignis-fb-required { color: #ef4444; margin-left: 4px; }
  .ignis-fb-input, .ignis-fb-select, .ignis-fb-textarea {
    width: 100%;
    padding: 10px 12px;
    border-radius: 9px;
    border: 1px solid rgba(255,255,255,.12);
    background: rgba(255,255,255,.05);
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color .2s;
    font-family: inherit;
  }
  .ignis-fb-input:focus, .ignis-fb-select:focus, .ignis-fb-textarea:focus {
    border-color: rgba(245,158,11,.5);
  }
  .ignis-fb-textarea {
    min-height: 110px;
    resize: vertical;
    font-family: inherit;
    line-height: 1.5;
  }
  .ignis-fb-select option { background: #0d1b2e; }
  .ignis-fb-type-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  }
  .ignis-fb-type-card {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 10px;
    padding: 10px 8px;
    text-align: center;
    cursor: pointer;
    transition: all .15s;
    user-select: none;
  }
  .ignis-fb-type-card:hover { border-color: rgba(255,255,255,.25); }
  .ignis-fb-type-card.selected {
    background: rgba(245,158,11,.15);
    border-color: #f59e0b;
  }
  .ignis-fb-type-icon { font-size: 22px; margin-bottom: 3px; }
  .ignis-fb-type-name { font-size: 11px; font-weight: 700; color: #cbd5e1; }
  .ignis-fb-error {
    color: #ef4444; font-size: 12px; min-height: 16px; margin-bottom: 8px;
  }
  .ignis-fb-info {
    font-size: 12px; color: #64748b;
    background: rgba(59,130,246,.08);
    border: 1px solid rgba(59,130,246,.2);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 14px;
    line-height: 1.5;
  }
  .ignis-fb-info-warn {
    color: #fbbf24;
    background: rgba(245,158,11,.08);
    border-color: rgba(245,158,11,.25);
  }
  .ignis-fb-buttons {
    display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;
  }
  .ignis-fb-btn {
    padding: 11px 22px;
    border-radius: 10px;
    font-size: 14px; font-weight: 700;
    cursor: pointer; border: none;
    font-family: inherit;
    transition: all .2s;
  }
  .ignis-fb-btn-cancel {
    background: rgba(255,255,255,.06);
    color: #94a3b8;
    border: 1px solid rgba(255,255,255,.1);
  }
  .ignis-fb-btn-cancel:hover { background: rgba(255,255,255,.1); color: #fff; }
  .ignis-fb-btn-send {
    background: linear-gradient(135deg, #f59e0b, #dc2626);
    color: #fff;
  }
  .ignis-fb-btn-send:hover { transform: translateY(-1px); }
  .ignis-fb-btn-send:disabled { opacity: .5; cursor: not-allowed; transform: none; }

  /* FAQ */
  .ignis-faq-search {
    width: 100%;
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.1);
    color: #fff;
    font-size: 14px;
    margin-bottom: 14px;
    font-family: inherit;
    outline: none;
  }
  .ignis-faq-search:focus { border-color: rgba(245,158,11,.5); }
  .ignis-faq-item {
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px;
    margin-bottom: 8px;
    overflow: hidden;
  }
  .ignis-faq-q {
    padding: 13px 16px;
    cursor: pointer;
    font-size: 14px; font-weight: 600;
    display: flex; justify-content: space-between; align-items: center;
    transition: background .15s;
  }
  .ignis-faq-q:hover { background: rgba(245,158,11,.05); }
  .ignis-faq-q-arrow {
    color: #f59e0b; font-size: 14px;
    transition: transform .2s;
  }
  .ignis-faq-item.open .ignis-faq-q-arrow { transform: rotate(90deg); }
  .ignis-faq-a {
    padding: 0 16px;
    max-height: 0;
    overflow: hidden;
    transition: max-height .3s ease, padding .3s ease;
    color: #cbd5e1;
    font-size: 13.5px;
    line-height: 1.6;
  }
  .ignis-faq-item.open .ignis-faq-a {
    max-height: 500px;
    padding: 4px 16px 14px;
  }
  .ignis-faq-a strong { color: #fbbf24; }
  .ignis-faq-a code {
    background: rgba(0,0,0,.4);
    padding: 1px 6px; border-radius: 4px;
    font-size: 12px;
    color: #fbbf24;
  }
  .ignis-faq-empty {
    text-align: center; padding: 20px;
    color: #64748b; font-size: 13px;
  }

  /* Tour guidé : overlay sombre avec "trou" */
  .ignis-tour-overlay {
    position: fixed; inset: 0;
    z-index: 999992;
    pointer-events: none;
  }
  .ignis-tour-overlay::before {
    content: '';
    position: fixed; inset: 0;
    background: rgba(0,0,0,.7);
    pointer-events: auto;
  }
  .ignis-tour-hole {
    position: fixed;
    border-radius: 12px;
    box-shadow: 0 0 0 9999px rgba(0,0,0,.75),
                0 0 0 3px #f59e0b,
                0 0 30px rgba(245,158,11,.6);
    pointer-events: none;
    transition: all .4s cubic-bezier(.4,0,.2,1);
    z-index: 999993;
  }

  /* Bulle d'explication */
  .ignis-tour-bubble {
    position: fixed;
    background: #0d1b2e;
    border: 1px solid rgba(245,158,11,.4);
    border-radius: 14px;
    padding: 18px 20px;
    max-width: 360px;
    box-shadow: 0 20px 60px rgba(0,0,0,.6);
    z-index: 999994;
    pointer-events: auto;
    transition: all .4s cubic-bezier(.4,0,.2,1);
    font-family: 'Source Sans Pro', sans-serif;
    color: #fff;
  }
  .ignis-tour-step-num {
    color: #f59e0b; font-size: 11px;
    font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .ignis-tour-title {
    font-size: 17px; font-weight: 800;
    color: #fff;
    margin-bottom: 8px;
  }
  .ignis-tour-text {
    font-size: 14px; color: #cbd5e1;
    line-height: 1.55;
    margin-bottom: 14px;
  }
  .ignis-tour-controls {
    display: flex; justify-content: space-between; align-items: center;
    gap: 10px;
  }
  .ignis-tour-progress {
    color: #64748b; font-size: 12px;
  }
  .ignis-tour-buttons { display: flex; gap: 8px; }
  .ignis-tour-btn {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px; font-weight: 700;
    cursor: pointer;
    border: none;
    transition: all .2s;
    font-family: inherit;
  }
  .ignis-tour-btn-prev {
    background: rgba(255,255,255,.08);
    color: #cbd5e1;
  }
  .ignis-tour-btn-prev:hover { background: rgba(255,255,255,.15); }
  .ignis-tour-btn-prev:disabled { opacity: .3; cursor: not-allowed; }
  .ignis-tour-btn-next {
    background: #f59e0b;
    color: #111;
  }
  .ignis-tour-btn-next:hover { background: #fbbf24; }
  .ignis-tour-btn-skip {
    background: none;
    color: #64748b;
    text-decoration: underline;
    font-weight: 500;
    font-size: 12px;
    padding: 4px 8px;
  }
  .ignis-tour-btn-skip:hover { color: #ef4444; }

  /* Sur petits écrans */
  @media (max-width: 600px) {
    .ignis-tour-bubble { max-width: calc(100vw - 32px); }
    .ignis-fb-type-row { grid-template-columns: repeat(2, 1fr); }
  }
  `;

  // Injecter le CSS
  var styleEl = document.createElement('style');
  styleEl.id = 'ignis-tour-styles';
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ─────────────────────────────────────────────────────────────
  // FAQ — contenu pré-rempli
  // ─────────────────────────────────────────────────────────────
  var FAQ = [
    {
      q: "Comment ajouter un sapeur à l'astreinte ?",
      a: "Ouvre le <strong>panneau Personnel</strong> sur le côté droit (clique sur l'onglet vertical). Tu vois la liste des sapeurs disponibles. <strong>Glisse-dépose</strong> un nom dans une des cases du tableau (Sous-officiers, Hommes du rang, etc.). C'est aussi simple que ça."
    },
    {
      q: "Comment marquer un engin indisponible ou réservé ?",
      a: "Clique sur un <strong>engin</strong> dans le tableau (FPT, VSAV, etc.). Une boîte de dialogue s'ouvre où tu peux : le marquer indisponible, lui ajouter une note, ou le réserver pour un créneau précis. Les engins indisponibles apparaissent en rouge."
    },
    {
      q: "Comment changer la semaine affichée ?",
      a: "Utilise les boutons <code>← Semaine</code> et <code>Semaine →</code> en haut du tableau pour naviguer. <code>Aujourd'hui</code> te ramène à la semaine en cours. Tu peux aussi cliquer sur la date affichée pour ouvrir un calendrier."
    },
    {
      q: "Comment imprimer le tableau ?",
      a: "Clique sur le bouton <strong>🖨 Imprimer</strong> en bas à droite. Une fenêtre d'impression s'ouvre avec une mise en page optimisée. Tu peux imprimer en PDF si tu veux archiver, ou directement sur ton imprimante."
    },
    {
      q: "Comment passer en mode TV (affichage salle de garde) ?",
      a: "Clique sur le bouton <strong>📺 TV</strong> en bas à droite. L'interface bascule en plein écran avec une rotation automatique des onglets toutes les 8 secondes. Idéal pour un écran fixe en salle de garde. Pour quitter : touche <code>Échap</code> ou bouton Quitter."
    },
    {
      q: "Comment revenir au portail IGNIS (changer de centre) ?",
      a: "Clique sur la <strong>petite voiture rouge 🚒</strong> en bas à droite (à côté du bouton TV). Tu reviens au portail d'accueil où tu peux choisir un autre centre de secours."
    },
    {
      q: "Comment importer le personnel depuis un fichier Excel ?",
      a: "Va dans <strong>⚙️ Réglages</strong> (clé à molette en bas à droite). Connecte-toi avec le code admin du CIS. Tu trouves un bouton <strong>Importer personnel</strong> — sélectionne ton fichier <code>.xlsx</code>. Un modèle est disponible sur demande."
    },
    {
      q: "À quoi sert chaque onglet du tableau ?",
      a: "<strong>Astreinte</strong> : qui est de service cette semaine. <strong>Vérifications</strong> : les vérifs hebdo des engins. <strong>Casernement</strong> : qui est en garde 24h. <strong>Infos hebdo</strong> : actualités du centre. <strong>Voies barrées</strong> : carte des routes coupées. <strong>GLI</strong> : grand livre d'intervention. <strong>Formation</strong> : planning des manœuvres. <strong>Réponse op.</strong> : capacité opérationnelle. <strong>Infos amicale</strong> : événements du centre."
    },
    {
      q: "La météo / les vigicrues ne s'affichent pas, que faire ?",
      a: "Vérifie ta connexion internet — la météo vient de Météo-France via le serveur. Si le serveur tourne mais que rien ne s'affiche, redémarre-le via <code>IGNIS_arreter.vbs</code> puis <code>IGNIS_demarrer.vbs</code>. Si le souci persiste, ouvre la console (F12) et regarde les erreurs en rouge."
    },
    {
      q: "Comment ajouter un nouveau sapeur dans la base ?",
      a: "Va dans <strong>⚙️ Réglages</strong> → <strong>Gérer le personnel</strong>. Tu peux ajouter, modifier ou désactiver des sapeurs un par un. Pour un ajout en masse, utilise plutôt l'import Excel."
    },
    {
      q: "Mes modifications sont-elles enregistrées automatiquement ?",
      a: "<strong>Oui, en temps réel</strong>. Chaque drag & drop, chaque clic, chaque note est sauvegardée immédiatement dans la base de données du centre. Un petit indicateur en haut à droite te confirme la sauvegarde."
    },
    {
      q: "Plusieurs personnes peuvent-elles utiliser l'appli en même temps ?",
      a: "Oui ! Le serveur tourne sur un PC et n'importe qui sur le même réseau peut s'y connecter via <code>http://[IP-du-serveur]:5010</code>. Les modifications se synchronisent automatiquement entre tous les écrans."
    },
    {
      q: "Comment changer le code administrateur de mon CIS ?",
      a: "Dans <strong>⚙️ Réglages</strong>, connecte-toi avec le code actuel, puis va dans <strong>Sécurité</strong>. Tu peux y changer le code admin du centre. Le code super-admin (général) se change dans le fichier <code>settings.json</code>."
    },
    {
      q: "Mes données sont-elles sauvegardées en cas de plantage du PC ?",
      a: "Les données sont stockées dans des fichiers <code>.db</code> du dossier <code>databases/</code>. Pour une vraie sécurité, fais des <strong>copies régulières</strong> de ce dossier sur une clé USB ou un disque externe. Tu peux aussi le sauvegarder sur un cloud si tu n'es pas en service actif."
    }
  ];

  // ─────────────────────────────────────────────────────────────
  // Étapes du tour guidé
  // Chaque étape : selectors (essais multiples) + title + text + position
  // ─────────────────────────────────────────────────────────────
  var TOUR_STEPS = [
    {
      selectors: null,  // étape introductive (pas de surbrillance)
      title: "Bienvenue sur IGNIS 🚒",
      text: "Cette application centralise toute la gestion de ton centre de secours : astreinte, gardes, engins, formations… On va faire un petit tour en 2 minutes pour que tu sois opérationnel.",
      position: 'center'
    },
    {
      selectors: ['header', '.header', '[class*="header"]', 'h1', '.cis-name', '.centre-nom'],
      title: "L'en-tête",
      text: "Ici tu retrouves le nom de ton centre, la date du jour et l'heure en temps réel. Le citation au-dessus change tous les jours pour la motivation 💪",
      position: 'bottom'
    },
    {
      selectors: ['.tabs', '[role="tablist"]', '.onglets', 'nav', '.nav-tabs'],
      title: "Les onglets",
      text: "Chaque onglet est une rubrique : Astreinte, Vérifications, Casernement… Clique pour passer de l'un à l'autre. Tu peux personnaliser leur ordre dans les réglages.",
      position: 'bottom'
    },
    {
      selectors: ['.tableau', 'main', '[class*="grid"]', '.content', '#app'],
      title: "Le tableau principal",
      text: "C'est le cœur de l'appli. Tu y vois qui est de service, quels engins sont disponibles, et tu peux ajouter du personnel par <strong>glisser-déposer</strong>.",
      position: 'top'
    },
    {
      selectors: ['[class*="personnel"]', '.sidebar', '.panel-personnel', 'aside'],
      title: "Le panneau Personnel",
      text: "Ouvre ce panneau sur le côté pour voir tous tes sapeurs. <strong>Glisse un nom</strong> dans une case du tableau pour l'affecter. C'est instantané et sauvegardé automatiquement.",
      position: 'left'
    },
    {
      selectors: ['button[onclick*="print"]', '[class*="imprimer"]', '[title*="Imprim"]'],
      title: "Imprimer 🖨",
      text: "Génère un PDF propre du tableau de la semaine. Idéal pour l'afficher au mur ou archiver.",
      position: 'top'
    },
    {
      selectors: ['button[onclick*="TV"]', '[class*="tv-mode"]', '[title*="TV"]'],
      title: "Mode TV 📺",
      text: "Passe en plein écran avec rotation automatique des onglets. À utiliser sur un écran fixe en salle de garde pour que tout le monde voie l'info à jour.",
      position: 'top'
    },
    {
      selectors: ['button[onclick*="ignisRetour"]', '[class*="retour-accueil"]', '[title*="accueil"]'],
      title: "Retour au portail",
      text: "La petite voiture rouge te ramène au portail IGNIS pour changer de centre. Ton travail reste sauvegardé sur ce centre.",
      position: 'top'
    },
    {
      selectors: ['#ignis-help-btn'],
      title: "Le bouton d'aide ❓",
      text: "Et voilà ! Tu peux relancer cette visite ou consulter la FAQ à tout moment depuis ce bouton. Bon démarrage avec IGNIS ! 🔥",
      position: 'top-left'
    }
  ];

  // ─────────────────────────────────────────────────────────────
  // Utilitaires
  // ─────────────────────────────────────────────────────────────
  function $(sel, root) {
    try { return (root || document).querySelector(sel); } catch(e) { return null; }
  }

  function findFirstMatch(selectors) {
    if (!selectors || !selectors.length) return null;
    for (var i = 0; i < selectors.length; i++) {
      var el = $(selectors[i]);
      if (el && isVisible(el)) return el;
    }
    return null;
  }

  function isVisible(el) {
    if (!el || !el.getBoundingClientRect) return false;
    var r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    var st = window.getComputedStyle(el);
    return st.display !== 'none' && st.visibility !== 'hidden' && st.opacity !== '0';
  }

  function scrollIntoViewIfNeeded(el) {
    if (!el) return;
    var r = el.getBoundingClientRect();
    var vh = window.innerHeight;
    if (r.top < 80 || r.bottom > vh - 100) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  // ─────────────────────────────────────────────────────────────
  // BOUTON FLOTTANT
  // ─────────────────────────────────────────────────────────────
  function createHelpButton() {
    if (document.getElementById('ignis-help-btn')) return;
    var btn = document.createElement('button');
    btn.id = 'ignis-help-btn';
    btn.title = 'Aide & visite guidée';
    btn.addEventListener('click', openMainMenu);
    document.body.appendChild(btn);
  }

  // ─────────────────────────────────────────────────────────────
  // MENU PRINCIPAL (choix tour / FAQ)
  // ─────────────────────────────────────────────────────────────
  function openMainMenu() {
    closeAll();
    var overlay = document.createElement('div');
    overlay.className = 'ignis-modal-overlay';
    overlay.id = 'ignis-menu-overlay';
    overlay.innerHTML = `
      <div class="ignis-modal-box" style="max-width: 480px;">
        <div class="ignis-modal-title">
          <span>👋 Besoin d'aide ?</span>
          <button class="ignis-modal-close">✕</button>
        </div>
        <div class="ignis-modal-subtitle">Choisis comment je peux t'aider à utiliser IGNIS.</div>
        <div class="ignis-tile-grid ignis-tile-grid-3">
          <div class="ignis-tile" id="ignis-tile-tour">
            <div class="ignis-tile-icon">🎯</div>
            <div class="ignis-tile-name">Visite guidée</div>
            <div class="ignis-tile-sub">Un tour de l'appli en 2 minutes</div>
          </div>
          <div class="ignis-tile" id="ignis-tile-faq">
            <div class="ignis-tile-icon">❓</div>
            <div class="ignis-tile-name">Questions fréquentes</div>
            <div class="ignis-tile-sub">Réponses rapides aux questions courantes</div>
          </div>
          <div class="ignis-tile" id="ignis-tile-feedback">
            <div class="ignis-tile-icon">💬</div>
            <div class="ignis-tile-name">Envoyer un feedback</div>
            <div class="ignis-tile-sub">Idée, bug, amélioration…</div>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeAll();
    });
    overlay.querySelector('.ignis-modal-close').addEventListener('click', closeAll);
    overlay.querySelector('#ignis-tile-tour').addEventListener('click', function() {
      closeAll();
      startTour();
    });
    overlay.querySelector('#ignis-tile-faq').addEventListener('click', function() {
      closeAll();
      openFAQ();
    });
    overlay.querySelector('#ignis-tile-feedback').addEventListener('click', function() {
      closeAll();
      openFeedback();
    });
  }

  // ─────────────────────────────────────────────────────────────
  // FAQ
  // ─────────────────────────────────────────────────────────────
  function openFAQ() {
    closeAll();
    var overlay = document.createElement('div');
    overlay.className = 'ignis-modal-overlay';
    overlay.id = 'ignis-faq-overlay';

    var itemsHtml = FAQ.map(function(item, i) {
      return `<div class="ignis-faq-item" data-idx="${i}">
        <div class="ignis-faq-q">
          <span>${item.q}</span>
          <span class="ignis-faq-q-arrow">▶</span>
        </div>
        <div class="ignis-faq-a">${item.a}</div>
      </div>`;
    }).join('');

    overlay.innerHTML = `
      <div class="ignis-modal-box">
        <div class="ignis-modal-title">
          <span>❓ Questions fréquentes</span>
          <button class="ignis-modal-close">✕</button>
        </div>
        <div class="ignis-modal-subtitle">Clique sur une question pour voir la réponse.</div>
        <input type="text" class="ignis-faq-search" id="ignis-faq-search" placeholder="🔍 Rechercher…">
        <div id="ignis-faq-list">${itemsHtml}</div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeAll();
    });
    overlay.querySelector('.ignis-modal-close').addEventListener('click', closeAll);

    // Toggle des questions
    overlay.querySelectorAll('.ignis-faq-q').forEach(function(q) {
      q.addEventListener('click', function() {
        q.parentElement.classList.toggle('open');
      });
    });

    // Recherche
    var searchInput = overlay.querySelector('#ignis-faq-search');
    searchInput.addEventListener('input', function() {
      var query = searchInput.value.toLowerCase().trim();
      var list = overlay.querySelector('#ignis-faq-list');
      var visibleCount = 0;
      list.querySelectorAll('.ignis-faq-item').forEach(function(item) {
        var idx = parseInt(item.dataset.idx);
        var faq = FAQ[idx];
        var match = !query ||
                    faq.q.toLowerCase().indexOf(query) >= 0 ||
                    faq.a.toLowerCase().indexOf(query) >= 0;
        item.style.display = match ? '' : 'none';
        if (match) visibleCount++;
      });
      // Message si rien trouvé
      var emptyMsg = list.querySelector('.ignis-faq-empty');
      if (visibleCount === 0) {
        if (!emptyMsg) {
          emptyMsg = document.createElement('div');
          emptyMsg.className = 'ignis-faq-empty';
          emptyMsg.textContent = 'Aucune question ne correspond à ta recherche.';
          list.appendChild(emptyMsg);
        }
      } else if (emptyMsg) {
        emptyMsg.remove();
      }
    });
    setTimeout(function(){ searchInput.focus(); }, 100);
  }

  // ─────────────────────────────────────────────────────────────
  // FEEDBACK
  // ─────────────────────────────────────────────────────────────
  var FEEDBACK_TYPES = [
    { id: 'idee',       name: 'Idée',         icon: '💡' },
    { id: 'bug',        name: 'Bug',          icon: '🐛' },
    { id: 'ameliore',   name: 'Amélioration', icon: '✨' },
    { id: 'autre',      name: 'Autre',        icon: '💬' }
  ];

  // Récupère l'email admin depuis le serveur (cache)
  var _adminEmailCache = null;
  function getAdminEmail() {
    return new Promise(function(resolve) {
      if (_adminEmailCache !== null) { resolve(_adminEmailCache); return; }
      fetch('/api/cis').then(function(r){ return r.json(); }).then(function(data){
        _adminEmailCache = (data.settings && data.settings.admin_email) || '';
        resolve(_adminEmailCache);
      }).catch(function(){ resolve(''); });
    });
  }

  function openFeedback() {
    closeAll();

    var typesHtml = FEEDBACK_TYPES.map(function(t, i) {
      return `<div class="ignis-fb-type-card${i === 0 ? ' selected' : ''}" data-type="${t.id}" data-name="${t.name}">
        <div class="ignis-fb-type-icon">${t.icon}</div>
        <div class="ignis-fb-type-name">${t.name}</div>
      </div>`;
    }).join('');

    var overlay = document.createElement('div');
    overlay.className = 'ignis-modal-overlay';
    overlay.id = 'ignis-feedback-overlay';
    overlay.innerHTML = `
      <div class="ignis-modal-box">
        <div class="ignis-modal-title">
          <span>💬 Envoyer un feedback</span>
          <button class="ignis-modal-close">✕</button>
        </div>
        <div class="ignis-modal-subtitle">
          Une idée, un bug, une suggestion d'amélioration ? Partage-la avec l'administrateur.
        </div>

        <div id="ignis-fb-info-box" class="ignis-fb-info">
          <span id="ignis-fb-info-text">⏳ Chargement…</span>
        </div>

        <div class="ignis-fb-group">
          <label class="ignis-fb-label">Type de retour</label>
          <div class="ignis-fb-type-row" id="ignis-fb-types">${typesHtml}</div>
        </div>

        <div class="ignis-fb-group">
          <label class="ignis-fb-label">Sujet <span class="ignis-fb-required">*</span></label>
          <input type="text" class="ignis-fb-input" id="ignis-fb-subject"
                 placeholder="Ex : Impossible d'imprimer en mode TV" maxlength="120">
        </div>

        <div class="ignis-fb-group">
          <label class="ignis-fb-label">Description <span class="ignis-fb-required">*</span></label>
          <textarea class="ignis-fb-textarea" id="ignis-fb-message"
                    placeholder="Décris ton retour le plus précisément possible…"></textarea>
        </div>

        <div class="ignis-fb-group">
          <label class="ignis-fb-label">Ton e-mail (facultatif, pour recevoir une réponse)</label>
          <input type="email" class="ignis-fb-input" id="ignis-fb-email"
                 placeholder="ton.email@exemple.fr">
        </div>

        <div class="ignis-fb-error" id="ignis-fb-error"></div>

        <div class="ignis-fb-buttons">
          <button class="ignis-fb-btn ignis-fb-btn-cancel" id="ignis-fb-cancel">Annuler</button>
          <button class="ignis-fb-btn ignis-fb-btn-send" id="ignis-fb-send">📧 Envoyer</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeAll();
    });
    overlay.querySelector('.ignis-modal-close').addEventListener('click', closeAll);
    overlay.querySelector('#ignis-fb-cancel').addEventListener('click', closeAll);

    // Sélection du type
    var selectedType = FEEDBACK_TYPES[0];
    overlay.querySelectorAll('.ignis-fb-type-card').forEach(function(card) {
      card.addEventListener('click', function() {
        overlay.querySelectorAll('.ignis-fb-type-card').forEach(function(c){ c.classList.remove('selected'); });
        card.classList.add('selected');
        selectedType = FEEDBACK_TYPES.find(function(t){ return t.id === card.dataset.type; });
      });
    });

    // Charger l'email admin et mettre à jour l'info
    getAdminEmail().then(function(email) {
      var info = overlay.querySelector('#ignis-fb-info-box');
      var infoText = overlay.querySelector('#ignis-fb-info-text');
      if (!info || !infoText) return;
      if (email) {
        info.classList.remove('ignis-fb-info-warn');
        infoText.innerHTML = '📧 Ton message sera envoyé à <strong>' + escapeHtml(email) + '</strong>. Ton client e-mail s\'ouvrira avec tout pré-rempli — il te suffira de cliquer sur Envoyer.';
      } else {
        info.classList.add('ignis-fb-info-warn');
        infoText.innerHTML = '⚠️ Aucune adresse e-mail administrateur n\'a été configurée. Demande au super-administrateur de l\'ajouter dans le portail IGNIS (⚙️ Gérer les centres → Paramètres globaux).';
        var sendBtn = overlay.querySelector('#ignis-fb-send');
        if (sendBtn) sendBtn.disabled = true;
      }
    });

    // Bouton Envoyer
    overlay.querySelector('#ignis-fb-send').addEventListener('click', function() {
      submitFeedback(overlay, selectedType);
    });

    setTimeout(function(){
      var s = overlay.querySelector('#ignis-fb-subject');
      if (s) s.focus();
    }, 100);
  }

  function submitFeedback(overlay, selectedType) {
    var subject = overlay.querySelector('#ignis-fb-subject').value.trim();
    var message = overlay.querySelector('#ignis-fb-message').value.trim();
    var userEmail = overlay.querySelector('#ignis-fb-email').value.trim();
    var errEl = overlay.querySelector('#ignis-fb-error');
    errEl.textContent = '';

    // Validation
    if (!subject) { errEl.textContent = '⚠️ Le sujet est obligatoire.'; return; }
    if (!message) { errEl.textContent = '⚠️ La description est obligatoire.'; return; }
    if (userEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(userEmail)) {
      errEl.textContent = '⚠️ Le format de ton e-mail est invalide.';
      return;
    }

    getAdminEmail().then(function(adminEmail) {
      if (!adminEmail) {
        errEl.textContent = '⚠️ Aucune adresse administrateur configurée.';
        return;
      }

      // Récupérer le contexte (centre, URL)
      var cisId = (location.pathname.split('/cis/')[1] || '').split('/')[0] || 'inconnu';
      var nowISO = new Date().toLocaleString('fr-FR');

      // Construire le sujet et le corps
      var mailSubject = '[IGNIS – ' + selectedType.name + '] ' + subject;
      var mailBody = [
        '─────────────────────────────────────────',
        ' FEEDBACK IGNIS NOVA',
        '─────────────────────────────────────────',
        '',
        'Type        : ' + selectedType.icon + ' ' + selectedType.name,
        'Sujet       : ' + subject,
        'Centre      : ' + cisId,
        'Date        : ' + nowISO,
        'Page        : ' + location.href,
        (userEmail ? 'Répondre à  : ' + userEmail : 'Répondre à  : (non renseigné)'),
        '',
        '─────────────────────────────────────────',
        ' MESSAGE',
        '─────────────────────────────────────────',
        '',
        message,
        '',
        '─────────────────────────────────────────',
        '— Envoyé depuis IGNIS NOVA'
      ].join('\n');

      // Construire le mailto et l'ouvrir
      var mailtoUrl = 'mailto:' + encodeURIComponent(adminEmail)
                    + '?subject=' + encodeURIComponent(mailSubject)
                    + '&body=' + encodeURIComponent(mailBody);

      // Vérifier que l'URL n'est pas trop longue (limite ~2000 chars sur certains OS)
      if (mailtoUrl.length > 2000) {
        // Tronquer le message si nécessaire
        var safeMessage = message.substring(0, 1200) + '…\n\n[message tronqué — le client mail a une limite de taille]';
        mailBody = mailBody.replace(message, safeMessage);
        mailtoUrl = 'mailto:' + encodeURIComponent(adminEmail)
                  + '?subject=' + encodeURIComponent(mailSubject)
                  + '&body=' + encodeURIComponent(mailBody);
      }

      // Ouvrir le client mail
      window.location.href = mailtoUrl;

      // Confirmation
      showFeedbackSuccess(overlay);
    });
  }

  function showFeedbackSuccess(overlay) {
    var box = overlay.querySelector('.ignis-modal-box');
    if (!box) return;
    box.innerHTML = `
      <div style="text-align:center;padding:20px;">
        <div style="font-size:60px;margin-bottom:10px;">📬</div>
        <div style="font-size:20px;font-weight:800;color:#22c55e;margin-bottom:10px;">
          Ton client e-mail s'est ouvert !
        </div>
        <div style="color:#cbd5e1;font-size:14px;line-height:1.6;margin-bottom:24px;">
          Vérifie que tout est bien rempli puis clique sur <strong>Envoyer</strong> dans ton client e-mail (Outlook, Mail, Gmail…).
          <br><br>
          <span style="color:#64748b;font-size:12.5px;">Si rien ne s'est ouvert, c'est que ton ordinateur n'a pas de client e-mail configuré. Tu peux copier ton message et l'envoyer manuellement.</span>
        </div>
        <button class="ignis-fb-btn ignis-fb-btn-send" onclick="document.getElementById('ignis-feedback-overlay').remove()">
          C'est bon, merci !
        </button>
      </div>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ─────────────────────────────────────────────────────────────
  // TOUR GUIDÉ
  // ─────────────────────────────────────────────────────────────
  var tourState = { idx: 0, overlay: null, hole: null, bubble: null };

  function startTour() {
    tourState.idx = 0;
    // Overlay sombre (pour bloquer les clics ailleurs)
    var overlay = document.createElement('div');
    overlay.className = 'ignis-tour-overlay';
    overlay.id = 'ignis-tour-overlay';
    document.body.appendChild(overlay);
    tourState.overlay = overlay;

    // Hole (rectangle surligné)
    var hole = document.createElement('div');
    hole.className = 'ignis-tour-hole';
    document.body.appendChild(hole);
    tourState.hole = hole;

    // Bubble
    var bubble = document.createElement('div');
    bubble.className = 'ignis-tour-bubble';
    document.body.appendChild(bubble);
    tourState.bubble = bubble;

    renderStep();
    window.addEventListener('resize', renderStep);
    window.addEventListener('keydown', tourKeyboard);
  }

  function tourKeyboard(e) {
    if (e.key === 'Escape') endTour();
    else if (e.key === 'ArrowRight' || e.key === 'Enter') nextStep();
    else if (e.key === 'ArrowLeft') prevStep();
  }

  function renderStep() {
    if (!tourState.overlay) return;
    var step = TOUR_STEPS[tourState.idx];
    var bubble = tourState.bubble;
    var hole = tourState.hole;

    // Trouver l'élément cible
    var target = step.selectors ? findFirstMatch(step.selectors) : null;

    if (target) {
      scrollIntoViewIfNeeded(target);
      // Attendre la fin du scroll avant de positionner
      setTimeout(function() {
        positionHole(target);
        positionBubble(step, target);
      }, 100);
    } else {
      // Pas de cible → cacher le hole, centrer la bulle
      hole.style.opacity = '0';
      hole.style.width = '0';
      hole.style.height = '0';
      positionBubble(step, null);
    }

    // Contenu de la bulle
    bubble.innerHTML = `
      <div class="ignis-tour-step-num">Étape ${tourState.idx + 1} / ${TOUR_STEPS.length}</div>
      <div class="ignis-tour-title">${step.title}</div>
      <div class="ignis-tour-text">${step.text}</div>
      <div class="ignis-tour-controls">
        <div class="ignis-tour-progress">
          <button class="ignis-tour-btn ignis-tour-btn-skip" id="ignis-tour-skip">Passer la visite</button>
        </div>
        <div class="ignis-tour-buttons">
          <button class="ignis-tour-btn ignis-tour-btn-prev" id="ignis-tour-prev" ${tourState.idx === 0 ? 'disabled' : ''}>‹ Précédent</button>
          <button class="ignis-tour-btn ignis-tour-btn-next" id="ignis-tour-next">${tourState.idx === TOUR_STEPS.length - 1 ? 'Terminer ✓' : 'Suivant ›'}</button>
        </div>
      </div>`;

    bubble.querySelector('#ignis-tour-prev').addEventListener('click', prevStep);
    bubble.querySelector('#ignis-tour-next').addEventListener('click', nextStep);
    bubble.querySelector('#ignis-tour-skip').addEventListener('click', endTour);
  }

  function positionHole(target) {
    var r = target.getBoundingClientRect();
    var pad = 6;
    var hole = tourState.hole;
    hole.style.opacity = '1';
    hole.style.left = (r.left - pad) + 'px';
    hole.style.top = (r.top - pad) + 'px';
    hole.style.width = (r.width + pad * 2) + 'px';
    hole.style.height = (r.height + pad * 2) + 'px';
  }

  function positionBubble(step, target) {
    var bubble = tourState.bubble;
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    var bw = 360, bh = 220; // estimation

    if (!target || step.position === 'center') {
      bubble.style.left = (vw / 2 - bw / 2) + 'px';
      bubble.style.top = (vh / 2 - bh / 2) + 'px';
      return;
    }

    var r = target.getBoundingClientRect();
    var pos = step.position || 'bottom';
    var left, top;

    switch(pos) {
      case 'top':
        left = r.left + r.width / 2 - bw / 2;
        top = r.top - bh - 20;
        if (top < 20) { pos = 'bottom'; }
        break;
      case 'left':
        left = r.left - bw - 20;
        top = r.top + r.height / 2 - bh / 2;
        if (left < 20) { pos = 'right'; }
        break;
      case 'right':
        left = r.right + 20;
        top = r.top + r.height / 2 - bh / 2;
        if (left + bw > vw - 20) { pos = 'left'; }
        break;
      case 'top-left':
        left = r.left - bw - 20;
        top = r.top - bh / 2;
        if (left < 20) left = 20;
        break;
      default: // bottom
        left = r.left + r.width / 2 - bw / 2;
        top = r.bottom + 20;
    }

    if (pos === 'bottom' && (!top || top + bh > vh - 20)) top = r.top - bh - 20;
    if (pos === 'right' && left + bw > vw - 20) left = r.left - bw - 20;

    // Clamp dans l'écran
    left = Math.max(16, Math.min(left, vw - bw - 16));
    top = Math.max(16, Math.min(top, vh - bh - 16));

    bubble.style.left = left + 'px';
    bubble.style.top = top + 'px';
  }

  function nextStep() {
    if (tourState.idx < TOUR_STEPS.length - 1) {
      tourState.idx++;
      renderStep();
    } else {
      endTour();
    }
  }
  function prevStep() {
    if (tourState.idx > 0) {
      tourState.idx--;
      renderStep();
    }
  }
  function endTour() {
    if (tourState.overlay) tourState.overlay.remove();
    if (tourState.hole) tourState.hole.remove();
    if (tourState.bubble) tourState.bubble.remove();
    tourState = { idx: 0, overlay: null, hole: null, bubble: null };
    window.removeEventListener('resize', renderStep);
    window.removeEventListener('keydown', tourKeyboard);
    // Marquer comme vu pour ne pas le proposer automatiquement à nouveau
    try { localStorage.setItem('ignis_tour_done', '1'); } catch(e) {}
  }

  // ─────────────────────────────────────────────────────────────
  // Fermer toutes les modales
  // ─────────────────────────────────────────────────────────────
  function closeAll() {
    document.querySelectorAll('.ignis-modal-overlay').forEach(function(el) { el.remove(); });
    endTour();
  }

  // ─────────────────────────────────────────────────────────────
  // Démarrage : créer le bouton + proposer le tour à la première visite
  // ─────────────────────────────────────────────────────────────
  function init() {
    createHelpButton();

    // Première visite → proposer le tour automatiquement après 2 secondes
    try {
      if (!localStorage.getItem('ignis_tour_done')) {
        setTimeout(function() {
          if (!document.getElementById('ignis-menu-overlay')) openMainMenu();
        }, 2500);
      }
    } catch(e) {}
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(init, 500);
  } else {
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(init, 500); });
  }

  // Exposer un point d'entrée pour relancer depuis ailleurs si besoin
  window.IGNIS_TOUR = {
    open: openMainMenu,
    tour: startTour,
    faq: openFAQ,
    feedback: openFeedback,
    reset: function() {
      try { localStorage.removeItem('ignis_tour_done'); } catch(e) {}
    }
  };
})();
