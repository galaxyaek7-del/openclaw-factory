// Umrah agency assistant: deterministic chat engine (Arabic, Algerian Darija, French).
//
// Status: SIMULATION. It runs on a fictional agency (agency_example.json). Nothing here is
// connected to WhatsApp, Telegram, e-mail or any phone line (NOT CONNECTED): a "hand-off" is a
// lead card kept in the session, nothing is sent to anyone.
//
// Rules inherited from lib/response_intents.js / lib/response_router.js (the earlier auto-reply
// system), kept on purpose:
//   - the first bot message always says it is an automated assistant;
//   - every fact (price, date, document, step) comes from the agency data, never from the model's
//     memory, so the assistant cannot invent a price: no LLM, no network, no API key;
//   - price negotiation, complaints and anything not understood are never answered with a guess:
//     they are handed to the human owner.
// Works in Node (tests) and in the browser (services/umrah_assistant/demo/index.html).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.UmrahAssistant = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ---------------------------------------------------------------- text normalisation
  const AR_INDIC = '\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669';
  function normalize(text) {
    let s = String(text == null ? '' : text).toLowerCase();
    s = s.replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x660));
    s = s.normalize('NFD').replace(/[\u0300-\u036f\u064b-\u065f\u0670\u0640]/g, '');
    s = s.replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي');
    s = s.replace(/[^\p{L}\p{N}\s+]/gu, ' ').replace(/\s+/g, ' ').trim();
    return s;
  }
  const HAS_ARABIC = /[؀-ۿ]/;
  const nkw = (list) => list.map((k) => normalize(k));

  // Whole-word-prefix match for Latin keywords (stems), substring match for Arabic ones
  // (Arabic glues prefixes such as و ب ل ال onto words).
  function hitLen(norm, kw) {
    if (!kw) return 0;
    if (HAS_ARABIC.test(kw)) return norm.includes(kw) ? kw.length : 0;
    const re = new RegExp('(^| )' + kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    return re.test(norm) ? kw.length : 0;
  }
  function has(norm, list) {
    return list.some((k) => hitLen(norm, k) > 0);
  }

  // ---------------------------------------------------------------- language detection
  const DZ_AR = nkw(['شحال', 'واش', 'علاش', 'كيفاش', 'وقتاش', 'فين', 'نحب', 'نبغي', 'بغيت', 'راني', 'راهو', 'كاين', 'كاش', 'تاع', 'نتاع',
    'بصح', 'ماشي', 'برك', 'دروك', 'باش', 'ديالي', 'ديال', 'حاب', 'نحجز', 'نروح', 'نسجل', 'نعرف', 'نكلم', 'نخلص', 'غالي', 'شوية', 'هاذي', 'هادو', 'مليح', 'وين', 'قداه', 'بقداش', 'علابالي', 'يخي', 'نتاعكم', 'عندكم']);
  const ARABIZI = nkw(['chhal', 'ch7al', 'cheh7al', 'chehal', 'wach', 'wesh', 'wech', 'kifach', 'kifeh', 'kifah', 'nheb', 'n7eb', 'nhebb', 'nebghi', 'nebgh',
    '3andkom', '3andek', '3andkoum', '3lach', 'waqtach', 'wa9tach', 'wakteh', 'rani', 'bessah', 'bsah', 'besah', 'mazal', 'kayen', 'kayn', 'khlass', 'saha', 'sahit', 'sa7it',
    'yatik', 'hadi', 'hada', 'dyal', 'ta3', 'nta3', 'nehjez', 'n7jez', 'nehjzou', 'nkhalles', 'ndir', 'ghali', 'ghalya', 'fndq', 'tayara', 'mrhba', 'marhba', 'salam', 'slm', 'ahla',
    'bghit', 'b9it', 'dzair', 'dzayer', 'mlih', 'mlih', 'fin', 'wen', 'chkoun', 'ch7al', 'qdach', '9edach', 'bqdach', 'tkalef', 'wra9', 'wara9', 'nhar', 'youm', 'ayam', 'rah']);
  const FRENCH = nkw(['bonjour', 'bonsoir', 'salut', 'je', 'veux', 'voudrais', 'souhaite', 'prix', 'combien', 'quand', 'quelle', 'quelles', 'quel', 'quels', 'documents', 'reserver', 'reservation',
    'sejour', 'depart', 'hotel', 'vol', 'pour', 'avec', 'les', 'des', 'est', 'vous', 'svp', 'merci', 'comment', 'faut', 'avez', 'avoir', 'une', 'un', 'nous', 'mon', 'ma', 'dossier', 'billet',
    'paiement', 'payer', 'acompte', 'pouvez', 'peut', 'est-ce', 'quoi', 'sont', 'dans', 'sur', 'agence', 'et', 'ou', 'le', 'la', 'du', 'de', 'en', 'au', 'aux', 'ce', 'cette', 'mes', 'ses', 'oui', 'non']);

  function detectLang(text, fallback) {
    const raw = String(text || '');
    const norm = normalize(raw);
    const ar = (raw.match(/[؀-ۿ]/g) || []).length;
    const lat = (raw.match(/[A-Za-zÀ-ÿ]/g) || []).length;
    if (ar === 0 && lat === 0) return fallback || null;
    if (ar >= lat) {
      const toks = norm.split(' ');
      const dz = toks.filter((t) => DZ_AR.some((k) => t === k || (k.length > 3 && t.includes(k)))).length;
      return dz > 0 ? 'dz' : 'ar';
    }
    const toks = norm.split(' ');
    let fr = 0; let az = 0;
    for (const t of toks) {
      if (FRENCH.includes(t)) fr += 1;
      if (ARABIZI.includes(t) || /^[a-z]*[2-9][a-z]+$|^[a-z]+[2-9]$/.test(t) && /[a-z]/.test(t) && !/^\d+$/.test(t)) az += 1;
    }
    if (az > fr) return 'dz';
    if (az === fr && az > 0) return fallback || 'fr';
    return 'fr';
  }

  // ---------------------------------------------------------------- keyword tables (normalised at load)
  const K = {
    greeting: nkw(['سلام', 'السلام', 'مرحبا', 'اهلا', 'هلا', 'صباح الخير', 'مساء الخير', 'bonjour', 'bonsoir', 'salut', 'salam', 'slm', 'coucou', 'hello', 'ahla', 'marhba', 'mrhba', 'cc']),
    thanks: nkw(['شكرا', 'جزاك', 'بارك الله', 'صحيت', 'صحه', 'يعطيك الصحه', 'merci', 'thanks', 'saha', 'sahit', 'sa7it', 'yatik', 'barakallah']),
    bye: nkw(['بالسلامه', 'مع السلامه', 'الي اللقاء', 'au revoir', 'a bientot', 'bslama', 'bsslama', 'bye']),
    human: nkw(['صاحب الوكاله', 'المسؤول', 'المدير', 'موظف', 'شخص حقيقي', 'انسان', 'نكلم', 'نتكلم مع', 'اتصل', 'تتصل', 'كلمني', 'رقم الهاتف', 'رقم هاتف', 'رقمكم', 'تليفون',
      'parler a', 'parler avec', 'conseiller', 'responsable', 'humain', 'telephone', 'appeler', 'appelez', 'numero', 'contacter', 'rappel', 'n3ayet', 'nkalem', 'nkelem', 'ntasal', 'telifon']),
    complaint: nkw(['شكوي', 'اشتكي', 'مشكل', 'مشكله', 'سيء', 'ما وصلني', 'استرجاع', 'نسترجع', 'تعويض', 'غش', 'نصب', 'نصابين', 'arnaque', 'probleme', 'plainte', 'rembours', 'escroc', 'decu', 'mecontent', 'mochkil', 'machkel', 'm4kel']),
    negotiation: nkw(['تخفيض', 'تخفيضات', 'نقص', 'انقص', 'تنقص', 'اخر سعر', 'سعر اخير', 'غالي', 'غاليه', 'مكلف', 'نتفاوض', 'تفاوض', 'remise', 'reduction', 'rabais', 'negocier', 'discount', 'dernier prix',
      'trop cher', 'ghali', 'ghalya', 'nogs', 'nokes', 'tnaqes']),
    religious: nkw(['مناسك', 'فتوي', 'حكم', 'يجوز', 'مبطلات', 'هل يجوز', 'fatwa', 'rituel', 'rite', 'licite', 'est ce permis', 'est-ce permis', 'jaiz']),
    cancel: nkw(['الغي', 'الغاء', 'ما نحبش', 'ما نبغيش', 'خلاص ما', 'annule', 'annuler', 'laisse tomber', 'ma n7ebch', 'ma nheb', 'cancel']),
    desire: nkw(['نحب', 'نبغي', 'بغيت', 'ابغي', 'اريد', 'حاب', 'حابه', 'نريد', 'ودي', 'je veux', 'je voudrais', 'je souhaite', 'on veut', 'nous voulons', 'nous souhaitons', 'je desire', 'nheb', 'n7eb', 'nebghi', 'bghit', 'bghina', 'nhebb']),
    book: nkw(['حجز', 'نحجز', 'احجز', 'نسجل', 'تسجيل', 'نسجلو', 'نحجزو', 'reserver', 'reservation', 'reserve', 'inscri', "m'inscrire", 'booker', 'nehjez', 'n7jez', 'nehjzou', 'nsajel', 'nsajjel', '7jz', 'hjz']),
    howq: nkw(['كيف', 'كيفاش', 'كيفيه', 'طريقه', 'خطوات', 'اجراءات', 'كيف يتم', 'comment', 'procedure', 'etapes', 'demarche', 'kifach', 'kifeh', 'kifah', 'kif']),
    ask: nkw(['شحال', 'كم', 'بكم', 'بكام', 'قداه', 'بقداش', 'وقتاش', 'متي', 'امتي', 'واش', 'هل', 'ماذا', 'ما هي', 'ما هو', 'quand', 'combien', 'quel', 'quelle', 'quels', 'quelles', 'est ce que', 'pourquoi', 'chhal', 'ch7al', 'wach', 'wech', 'waqtach', '9edach']),
    persons_words: nkw(['شخص', 'اشخاص', 'افراد', 'personne', 'personnes', 'adulte', 'adultes', 'pax', 'personat'])
  };

  // Info intents, scored by distinct keyword hits then the longest keyword (more specific wins).
  const INFO = {
    duration: nkw(['كم يوم', 'شحال من يوم', 'شحال من نهار', 'كم من يوم', 'عدد الايام', 'المده', 'مده الرحله', 'ايام', 'نهار', 'combien de jours', 'combien de temps', 'duree', 'nombre de jours', 'nuits',
      'chhal men nhar', 'ch7al men nhar', 'chhal men youm', 'ch7al men youm', 'ch7al nhar', 'nhar']),
    price: nkw(['سعر', 'اسعار', 'بكم', 'بكام', 'ثمن', 'تكلف', 'تكلفه', 'تكاليف', 'شحال', 'قداه', 'بقداش', 'كم يكلف', 'كم الباقه', 'كم تكلف', 'ارخص', 'اقل سعر', 'moins cher', 'moins chere', 'prix', 'tarif', 'combien', 'cout', 'coute', 'budget',
      'chhal', 'ch7al', 'cheh7al', 'chehal', '9edach', 'qdach', 'bqdach', 'tkalef', 'ch7al ta3']),
    dates: nkw(['موعد', 'مواعيد', 'تاريخ', 'تواريخ', 'متي', 'وقتاش', 'امتي', 'رحلات', 'الاقلاع', 'اقلاع', 'انطلاق', 'السفر', 'date', 'dates', 'quand', 'depart', 'departs', 'prochain', 'calendrier',
      'waqtach', 'wa9tach', 'imta', 'wakteh', 'wakt']),
    documents: nkw(['وثائق', 'وثيقه', 'اوراق', 'ورقه', 'ملف', 'جواز', 'باسبور', 'تطعيم', 'لقاح', 'صور', 'ماذا احتاج', 'واش نحتاج', 'واش لازم', 'شنو لازم', 'ماذا يلزم', 'اجيب', 'document', 'papier', 'papiers',
      'dossier', 'passeport', 'vaccin', 'photo', 'photos', 'pieces', 'que faut', 'quoi fournir', 'fournir', 'wara9', 'wra9', 'passport', 'wech lazem', 'wach lazem']),
    visa: nkw(['تاشيره', 'فيزا', 'visa', 'vise']),
    includes: nkw(['يشمل', 'تشمل', 'يتضمن', 'فندق', 'فنادق', 'اوتيل', 'طيران', 'رحله جويه', 'تذكره', 'وجبات', 'اكل', 'اطعام', 'مبيت', 'سكن', 'غرفه', 'غرف', 'قريب', 'مسافه', 'الحرم', 'النقل', 'حافله', 'مرشد',
      'inclus', 'compris', 'hotel', 'vol', 'avion', 'repas', 'petit dejeuner', 'chambre', 'distance', 'haram', 'transport', 'guide', 'logement', 'hebergement',
      'fndq', 'otel', 'tayara', '7aram', 'makla', 'wach fih', 'wech fih']),
    payment: nkw(['دفع', 'ادفع', 'ندفع', 'دفعه', 'تسبيق', 'عربون', 'مقدم', 'تقسيط', 'اقساط', 'بريدي', 'ccp', 'حواله', 'تحويل', 'نقدا', 'كاش', 'بنك', 'فاتوره', 'نخلص', 'تخلص', 'paiement', 'payer', 'acompte', 'avance',
      'versement', 'tranche', 'facilite', 'echelonne', 'virement', 'especes', 'baridimob', 'cheque', 'dfa3', 'ndfa3', 'tsbi9', '3arboun', 'nkhalles', 'khalles']),
    booking_how: nkw(['طريقه الحجز', 'خطوات الحجز', 'اجراءات الحجز', 'كيفيه الحجز', 'comment reserver', "comment s'inscrire", 'comment s inscrire', 'procedure', 'etapes', 'demarche', 'comment faire', 'comment ca marche']),
    packages: nkw(['باقات', 'باقه', 'عروض', 'العروض', 'برامج', 'برنامج', 'انواع', 'نوع', 'خيارات', 'offre', 'offres', 'formule', 'formules', 'package', 'packages', 'programme', 'programmes', 'categorie', 'categories', 'choix', '3orod', 'offer'])
  };

  // ---------------------------------------------------------------- formatting helpers
  const MONTHS = {
    ar: ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
    fr: ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
  };
  const fam = (lang) => (lang === 'fr' ? 'fr' : 'ar');
  const T = (lang, o) => (lang === 'fr' ? o.fr : lang === 'dz' ? (o.dz || o.ar) : o.ar);
  function money(n, lang, agency) {
    const s = String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return s + ' ' + agency.currency[fam(lang)];
  }
  function dateText(iso, lang) {
    const [y, m, d] = iso.split('-').map(Number);
    return d + ' ' + MONTHS[fam(lang)][m - 1] + ' ' + y;
  }
  const bullets = (arr) => arr.map((x) => '• ' + x).join('\n');
  const pname = (p, lang) => p.names[fam(lang)];
  const aname = (agency, lang) => agency.name[fam(lang)];

  function findPackage(agency, norm) {
    for (const p of agency.packages) {
      const names = [p.id, p.names.ar, p.names.fr].concat(p.aliases || []).map(normalize).filter(Boolean);
      if (names.some((k) => hitLen(norm, k) > 0)) return p;
    }
    return null;
  }

  // ---------------------------------------------------------------- replies (all facts from `agency`)
  const R = {
    disclosure(a, lang) {
      return T(lang, {
        ar: 'أنا المساعد الآلي ل' + aname(a, lang) + '. أجيبك عن الأسعار والمواعيد والوثائق وطريقة الحجز، وإذا كنت جاهزاً للحجز أحوّل طلبك لصاحب الوكالة.',
        dz: 'أنا المساعد الآلي تاع ' + aname(a, lang) + '. نجاوبك على الأسعار، المواعيد، الوثائق وكيفاش تحجز، وإذا حبيت تحجز نوصّل طلبك لصاحب الوكالة.',
        fr: "Je suis l'assistant automatique de " + aname(a, lang) + '. Je réponds sur les prix, les dates, les documents et la réservation, et je transmets votre demande au responsable quand vous êtes prêt(e) à réserver.'
      });
    },
    greeting(a, lang) {
      return T(lang, { ar: 'السلام عليكم 👋', dz: 'السلام عليكم 👋', fr: 'Bonjour 👋' });
    },
    menu(a, lang) {
      return T(lang, {
        ar: 'بماذا أساعدك؟ يمكنك أن تسأل عن: الأسعار، المواعيد، ما تشمله الباقة، الوثائق المطلوبة، طريقة الدفع أو الحجز.',
        dz: 'واش نقدر نخدمك؟ تقدر تسقسي على: الأسعار، المواعيد، واش تشمل الباقة، الوثائق، الدفع وكيفاش تحجز.',
        fr: 'Que puis-je faire pour vous ? Vous pouvez me demander : les prix, les dates, ce qui est inclus, les documents, le paiement ou la réservation.'
      });
    },
    packages(a, lang) {
      const lines = a.packages.map((p) => '• ' + pname(p, lang) + ' : ' + T(lang, { ar: p.days + ' يوماً', dz: p.days + ' يوم', fr: p.days + ' jours' }) + ' : ' + money(p.price_dzd, lang, a));
      return T(lang, {
        ar: 'عندنا ' + a.packages.length + ' باقات (السعر للشخص الواحد):\n' + lines.join('\n'),
        dz: 'عندنا ' + a.packages.length + ' باقات (السعر للشخص):\n' + lines.join('\n'),
        fr: 'Nous avons ' + a.packages.length + ' formules (prix par personne) :\n' + lines.join('\n')
      });
    },
    price(a, lang, p) {
      if (p) {
        return T(lang, {
          ar: 'الباقة ' + pname(p, lang) + ': ' + money(p.price_dzd, lang, a) + ' للشخص، لمدة ' + p.days + ' يوماً، في ' + p.room.ar + '.',
          dz: 'الباقة ' + pname(p, lang) + ': ' + money(p.price_dzd, lang, a) + ' للشخص، ' + p.days + ' يوم، في ' + p.room.ar + '.',
          fr: 'La formule ' + pname(p, lang) + ' : ' + money(p.price_dzd, lang, a) + ' par personne, ' + p.days + ' jours, en ' + p.room.fr + '.'
        });
      }
      return R.packages(a, lang) + '\n' + T(lang, {
        ar: 'أي باقة تهمك؟ أعطيك تفاصيلها.',
        dz: 'أنهي باقة تهمك؟ نعطيك تفاصيلها.',
        fr: 'Laquelle vous intéresse ? Je vous donne le détail.'
      });
    },
    dates(a, lang, p) {
      const list = a.departures.filter((d) => !p || d.packages.includes(p.id));
      const lines = list.map((d) => '• ' + dateText(d.date, lang) + (p ? '' : ' (' + d.packages.map((id) => pname(a.packages.find((x) => x.id === id), lang)).join(' / ') + ')'));
      return T(lang, {
        ar: 'مواعيد السفر' + (p ? ' للباقة ' + pname(p, lang) : '') + ':\n' + lines.join('\n') + '\n' + a.seats_note.ar,
        dz: 'مواعيد السفر' + (p ? ' للباقة ' + pname(p, lang) : '') + ':\n' + lines.join('\n') + '\n' + a.seats_note.ar,
        fr: 'Dates de départ' + (p ? ' pour la formule ' + pname(p, lang) : '') + ' :\n' + lines.join('\n') + '\n' + a.seats_note.fr
      });
    },
    documents(a, lang) {
      return T(lang, {
        ar: 'الوثائق المطلوبة:\n' + bullets(a.documents.ar) + '\n' + a.documents_note.ar,
        dz: 'الوثائق اللي لازمين:\n' + bullets(a.documents.ar) + '\n' + a.documents_note.ar,
        fr: 'Documents demandés :\n' + bullets(a.documents.fr) + '\n' + a.documents_note.fr
      });
    },
    visa(a, lang) {
      return T(lang, {
        ar: 'التأشيرة تتكفل بها الوكالة وهي مشمولة في السعر. تحتاج فقط لتسليم الوثائق.\n' + a.documents_note.ar,
        dz: 'الفيزا الوكالة هي اللي تتكفل بيها وداخلة في السعر. يلزمك غير تسلّم الوثائق.\n' + a.documents_note.ar,
        fr: "Le visa est pris en charge par l'agence et inclus dans le prix. Il suffit de déposer vos documents.\n" + a.documents_note.fr
      });
    },
    includes(a, lang, p) {
      const base = T(lang, {
        ar: 'الباقة تشمل:\n' + bullets(a.includes.ar) + '\nلا تشمل: ' + a.excludes.ar.join('، ') + '.',
        dz: 'الباقة تشمل:\n' + bullets(a.includes.ar) + '\nما تشملش: ' + a.excludes.ar.join('، ') + '.',
        fr: 'La formule comprend :\n' + bullets(a.includes.fr) + '\nNe comprend pas : ' + a.excludes.fr.join(', ') + '.'
      });
      if (!p) {
        const lines = a.packages.map((x) => '• ' + pname(x, lang) + ' : ' + T(lang, { ar: 'مكة ' + x.makkah.stars + '★ على بعد ' + x.makkah.distance_m + ' م، المدينة ' + x.madinah.stars + '★ على بعد ' + x.madinah.distance_m + ' م، ' + x.meals.ar, fr: 'La Mecque ' + x.makkah.stars + '★ à ' + x.makkah.distance_m + ' m, Médine ' + x.madinah.stars + '★ à ' + x.madinah.distance_m + ' m, ' + x.meals.fr }));
        return base + '\n\n' + T(lang, { ar: 'الفنادق حسب الباقة:', dz: 'الفنادق حسب الباقة:', fr: 'Hôtels selon la formule :' }) + '\n' + lines.join('\n');
      }
      return base + '\n\n' + T(lang, {
        ar: pname(p, lang) + ': مكة ' + p.makkah.stars + '★ على بعد ' + p.makkah.distance_m + ' م من الحرم، المدينة ' + p.madinah.stars + '★ على بعد ' + p.madinah.distance_m + ' م، ' + p.meals.ar + '، ' + p.room.ar + '.',
        fr: pname(p, lang) + ' : La Mecque ' + p.makkah.stars + '★ à ' + p.makkah.distance_m + ' m du Haram, Médine ' + p.madinah.stars + '★ à ' + p.madinah.distance_m + ' m, ' + p.meals.fr + ', ' + p.room.fr + '.'
      });
    },
    duration(a, lang) {
      const lines = a.packages.map((p) => '• ' + pname(p, lang) + ' : ' + T(lang, { ar: p.days + ' يوماً', dz: p.days + ' يوم', fr: p.days + ' jours' }));
      return T(lang, { ar: 'مدة الرحلة حسب الباقة:\n' + lines.join('\n'), dz: 'مدة الرحلة حسب الباقة:\n' + lines.join('\n'), fr: 'Durée du séjour selon la formule :\n' + lines.join('\n') });
    },
    payment(a, lang) {
      return T(lang, {
        ar: 'التسبيق ' + money(a.deposit_dzd, lang, a) + ' للشخص عند الحجز، والباقي قبل السفر بـ ' + a.balance_days_before + ' يوماً.\nطرق الدفع: ' + a.payment_methods.ar.join('، ') + '.',
        dz: 'التسبيق ' + money(a.deposit_dzd, lang, a) + ' للشخص كي تحجز، والباقي قبل السفر بـ ' + a.balance_days_before + ' يوم.\nطرق الدفع: ' + a.payment_methods.ar.join('، ') + '.',
        fr: "L'acompte est de " + money(a.deposit_dzd, lang, a) + ' par personne à la réservation, le solde ' + a.balance_days_before + ' jours avant le départ.\nModes de paiement : ' + a.payment_methods.fr.join(', ') + '.'
      });
    },
    booking_how(a, lang) {
      const num = (arr) => arr.map((x, i) => (i + 1) + '. ' + x).join('\n');
      return T(lang, {
        ar: 'خطوات الحجز:\n' + num(a.booking_steps.ar) + '\nإذا أردت أن نبدأ الآن اكتب «أريد الحجز».',
        dz: 'خطوات الحجز:\n' + num(a.booking_steps.ar) + '\nإذا حبيت نبداو دروك اكتب «نحب نحجز».',
        fr: 'Étapes de réservation :\n' + num(a.booking_steps.fr) + '\nPour commencer maintenant, écrivez « je veux réserver ».'
      });
    },
    religious(a, lang) {
      return T(lang, {
        ar: 'هذا السؤال يخص أحكام المناسك، ولا أجيب عنه حتى لا أخطئ. المرشد الديني المرافق للرحلة يجيبك، ويمكن لصاحب الوكالة تعريفك به. هل تريد أن أسجّل طلب اتصال؟',
        dz: 'هذا سؤال في أحكام المناسك وما نجاوبش عليه باش ما نغلطش. المرشد الديني اللي يرافقكم يجاوبك، وصاحب الوكالة يعرّفك بيه. تحب نسجّل لك طلب اتصال؟',
        fr: "Cette question relève des rites de la omra et je ne réponds pas à ce sujet pour ne pas me tromper. Le guide religieux de l'agence vous répondra. Voulez-vous que je note une demande d'appel ?"
      });
    },
    thanks(a, lang) {
      return T(lang, { ar: 'عفواً، في خدمتك. هل من سؤال آخر؟', dz: 'بالصحة، في الخدمة. عندك سؤال آخر؟', fr: "Avec plaisir. Avez-vous une autre question ?" });
    },
    bye(a, lang) {
      return T(lang, { ar: 'بالسلامة، وتقبّل الله منك. 🤲', dz: 'بالسلامة، وتقبّل الله منك. 🤲', fr: 'Au revoir, et que Dieu accepte votre omra. 🤲' });
    },
    fallback(a, lang) {
      return T(lang, {
        ar: 'لم أفهم سؤالك جيداً ولا أريد أن أخمّن. ' + 'يمكنك أن تسأل عن الأسعار أو المواعيد أو الوثائق أو الدفع أو الحجز، أو اكتب «صاحب الوكالة» ليتصل بك.',
        dz: 'ما فهمتش سؤالك مليح وما حبيتش نخمّن. تقدر تسقسي على الأسعار، المواعيد، الوثائق، الدفع أو الحجز، أو اكتب «صاحب الوكالة» باش يتصل بيك.',
        fr: "Je n'ai pas bien compris votre question et je préfère ne pas deviner. Vous pouvez me demander les prix, les dates, les documents, le paiement ou la réservation, ou écrire « responsable » pour être rappelé(e)."
      });
    }
  };

  // ---------------------------------------------------------------- hand-off flow
  const ASK = {
    package(a, lang) {
      const names = a.packages.map((p) => pname(p, lang)).join(' / ');
      return T(lang, { ar: 'ممتاز! أي باقة تريد؟ (' + names + ')', dz: 'ممتاز! أنهي باقة تحب؟ (' + names + ')', fr: 'Parfait ! Quelle formule souhaitez-vous ? (' + names + ')' });
    },
    persons(a, lang) {
      return T(lang, { ar: 'كم عدد الأشخاص المسافرين؟', dz: 'شحال من واحد راكم مسافرين؟', fr: 'Combien de personnes voyagent ?' });
    },
    name(a, lang) {
      return T(lang, { ar: 'ما اسمك الكامل؟', dz: 'واش هو سميتك؟', fr: 'Quel est votre nom complet ?' });
    },
    phone(a, lang) {
      return T(lang, { ar: 'ما رقم هاتفك ليتصل بك صاحب الوكالة؟', dz: 'واش هو رقم تيليفونك باش يتصل بيك صاحب الوكالة؟', fr: "Quel est votre numéro de téléphone pour que le responsable vous rappelle ?" });
    },
    phoneAgain(a, lang) {
      return T(lang, { ar: 'الرقم غير واضح. اكتبه هكذا: 0555123456', dz: 'الرقم ما ظهرش مليح. اكتبو هكذا: 0555123456', fr: 'Le numéro semble incorrect. Écrivez-le ainsi : 0555123456' });
    }
  };

  const NUM_WORDS = {
    1: nkw(['واحد', 'وحدي', 'شخص واحد', 'seul', 'seule', 'un', 'une', 'wa7ed', 'wahed']),
    2: nkw(['اثنين', 'اتنين', 'جوج', 'زوج', 'شخصين', 'deux', 'jouj', 'zouj']),
    3: nkw(['ثلاثه', 'ثلاث', 'تلاته', 'تلاتة', 'trois', 'tleta', 'tlata']),
    4: nkw(['اربعه', 'اربع', 'quatre', 'arb3a', 'rb3a']),
    5: nkw(['خمسه', 'خمس', 'cinq', 'khamsa']),
    6: nkw(['سته', 'ست', 'six', 'setta']),
    7: nkw(['سبعه', 'سبع', 'sept', 'sb3a']),
    8: nkw(['ثمانيه', 'ثماني', 'huit', 'tmanya']),
    9: nkw(['تسعه', 'تسع', 'neuf', 'tis3a']),
    10: nkw(['عشره', 'عشر', 'dix', '3achra'])
  };
  function parsePersons(norm) {
    const m = norm.match(/\d+/);
    if (m) { const n = parseInt(m[0], 10); return n >= 1 && n <= 30 ? n : null; }
    for (let n = 10; n >= 1; n -= 1) if (has(norm, NUM_WORDS[n])) return n;
    return null;
  }
  function parsePhone(text) {
    const flat = String(text).replace(/[\u0660-\u0669]/g, (d) => String(AR_INDIC.indexOf(d))).replace(/[\s.\-()]/g, '');
    const m = flat.match(/(?:\+213|00213|213|0)([567]\d{8})/);
    return m ? '0' + m[1] : null;
  }
  function parseName(text) {
    let s = String(text).trim();
    if (/\d/.test(s)) return null;
    s = s.replace(/^(?:اسمي|سميتي|انا|أنا|ismi|ana|je m'appelle|je m appelle|je suis|mon nom est|nom\s*:)\s*/i, '').trim();
    const toks = s.split(/\s+/).filter(Boolean);
    if (toks.length < 1 || toks.length > 5 || s.length < 2 || s.length > 40) return null;
    return s;
  }

  function newSession() {
    return { lang: null, greeted: false, state: 'idle', reason: null, lead: { package: null, persons: null, name: null, phone: null },
      phoneTries: 0, unknownRun: 0, userLog: [], handoffs: [] };
  }

  function nextMissing(session) {
    const need = session.reason === 'ready_to_book' ? ['package', 'persons', 'name', 'phone'] : ['name', 'phone'];
    return need.find((f) => !session.lead[f]) || null;
  }

  function startHandoff(session, reason) {
    session.state = 'collecting';
    session.reason = reason;
    session.phoneTries = 0;
  }

  function finishHandoff(agency, session, lang) {
    const lead = Object.assign({}, session.lead);
    const pkg = lead.package ? agency.packages.find((p) => p.id === lead.package) : null;
    const card = {
      reason: session.reason, lang: session.lang, created_at: new Date().toISOString(),
      package: pkg ? pkg.names.fr : null, persons: lead.persons, name: lead.name, phone: lead.phone,
      estimate_dzd: pkg && lead.persons ? pkg.price_dzd * lead.persons : null,
      last_messages: session.userLog.slice(-4),
      delivery: 'NOT CONNECTED (demo: nothing was sent to anyone)'
    };
    session.handoffs.push(card);
    session.state = 'idle';
    session.reason = null;
    session.lead = { package: null, persons: null, name: null, phone: null };
    const est = card.estimate_dzd ? T(lang, {
      ar: '\nالمبلغ التقديري: ' + money(card.estimate_dzd, lang, agency) + ' (يؤكده صاحب الوكالة).',
      fr: '\nMontant estimé : ' + money(card.estimate_dzd, lang, agency) + ' (confirmé par le responsable).'
    }) : '';
    const text = T(lang, {
      ar: 'شكراً ' + card.name + '. حوّلت طلبك إلى صاحب الوكالة وسيتصل بك على ' + card.phone + ' في ساعات العمل (' + agency.hours.ar + ').' + est,
      dz: 'شكراً ' + card.name + '. وصّلت طلبك لصاحب الوكالة وراه يتصل بيك على ' + card.phone + ' في وقت الخدمة (' + agency.hours.ar + ').' + est,
      fr: 'Merci ' + card.name + '. J\'ai transmis votre demande au responsable, qui vous rappellera au ' + card.phone + ' (' + agency.hours.fr + ').' + est
    });
    return { text, card };
  }

  // ---------------------------------------------------------------- classification
  function bestInfo(norm) {
    let best = null; let bestHits = 0; let bestLen = -1;
    // 'packages' is a generic opener ("offers", "packages"): it only wins when nothing more specific matched
    const keys = Object.keys(INFO).filter((k) => k !== 'packages');
    for (const key of keys) {
      let hits = 0; let maxLen = -1; const seen = new Set();
      for (const k of INFO[key]) {
        const l = hitLen(norm, k);
        if (l && !seen.has(k)) { seen.add(k); hits += 1; maxLen = Math.max(maxLen, l); }
      }
      if (hits > 0 && (maxLen > bestLen || (maxLen === bestLen && hits > bestHits))) { best = key; bestHits = hits; bestLen = maxLen; }
    }
    if (!best && INFO.packages.some((k) => hitLen(norm, k) > 0)) return 'packages';
    return best;
  }

  function classify(norm) {
    if (has(norm, K.complaint)) return 'complaint';
    if (has(norm, K.negotiation)) return 'negotiation';
    if (has(norm, K.religious)) return 'religious';
    if (has(norm, K.human)) return 'human';
    const wantsBook = has(norm, K.book);
    const how = has(norm, K.howq);
    const asking = has(norm, K.ask);
    const info = bestInfo(norm);
    if (wantsBook && how) return 'booking_how';
    if (wantsBook && has(norm, K.desire) && !asking) return 'ready_to_book';
    if (wantsBook && !asking && !info && norm.split(' ').length <= 3) return 'ready_to_book_soft';
    if (info) return info;
    if (wantsBook) return 'booking_how';
    if (has(norm, K.thanks)) return 'thanks';
    if (has(norm, K.bye)) return 'bye';
    if (has(norm, K.greeting)) return 'greeting';
    return 'unknown';
  }

  // ---------------------------------------------------------------- main entry
  function respond(agency, session, message) {
    const text = String(message == null ? '' : message);
    const norm = normalize(text);
    const detected = detectLang(text, session.lang);
    const collecting = session.state === 'collecting';
    // while collecting numbers/names/phones the message carries no language signal: keep the session's
    if (detected && (!collecting || norm.split(' ').length > 3 || !session.lang)) session.lang = detected;
    const lang = session.lang || 'fr';
    session.userLog.push(text.slice(0, 200));

    const parts = [];
    let intent = null;
    let handoff = null;
    const firstTurn = !session.greeted;
    if (firstTurn) { session.greeted = true; parts.push(R.greeting(agency, lang) + ' ' + R.disclosure(agency, lang)); }

    const pkgMention = findPackage(agency, norm);

    if (!collecting && session.pendingOffer) {
      const po = session.pendingOffer;
      session.pendingOffer = null;
      if (wantsCallback(text)) {
        startHandoff(session, po.reason);
        parts.push(ASK.name(agency, lang));
        return { text: parts.join('\n\n'), intent: 'handoff_start', lang, handoff: null };
      }
    }

    if (collecting && has(norm, K.cancel)) {
      session.state = 'idle'; session.reason = null; session.lead = { package: null, persons: null, name: null, phone: null };
      parts.push(T(lang, { ar: 'تمام، ألغيت الطلب. أنا هنا إذا احتجت شيئاً.', dz: 'مرحبا، لغيت الطلب. أنا هنا كي تحتاج.', fr: "D'accord, j'ai annulé la demande. Je reste disponible." }));
      return { text: parts.join('\n\n'), intent: 'cancel', lang, handoff: null };
    }

    if (collecting) {
      const field = nextMissing(session);
      let accepted = false;
      if (field === 'package' && pkgMention) { session.lead.package = pkgMention.id; accepted = true; }
      else if (field === 'persons') { const n = parsePersons(norm); if (n) { session.lead.persons = n; accepted = true; } }
      else if (field === 'name') {
        const looksQuestion = has(norm, K.ask) || /[?؟]/.test(text);
        const nm = looksQuestion ? null : parseName(text);
        if (nm) { session.lead.name = nm; accepted = true; }
      } else if (field === 'phone') {
        const ph = parsePhone(text);
        if (ph) { session.lead.phone = ph; accepted = true; } else if (!has(norm, [].concat(Object.values(INFO).flat()))) { session.phoneTries += 1; }
      }
      if (accepted) {
        const missing = nextMissing(session);
        if (!missing) {
          const done = finishHandoff(agency, session, lang);
          parts.push(done.text);
          return { text: parts.join('\n\n'), intent: 'handoff_done', lang, handoff: done.card };
        }
        parts.push(ASK[missing](agency, lang));
        return { text: parts.join('\n\n'), intent: 'collecting', lang, handoff: null };
      }
      if (field === 'phone' && session.phoneTries >= 3) {
        // give up on the number rather than loop forever; the owner can still see the conversation
        const done = finishHandoff(agency, session, lang);
        done.card.phone = null;
        parts.push(T(lang, { ar: 'سجلت طلبك بدون رقم، سيتواصل معك صاحب الوكالة عبر هذه المحادثة.', dz: 'سجلت طلبك بلا رقم، صاحب الوكالة يتواصل معاك في هذه المحادثة.', fr: "J'ai noté votre demande sans numéro, le responsable vous répondra dans cette conversation." }));
        return { text: parts.join('\n\n'), intent: 'handoff_done', lang, handoff: done.card };
      }
      // not a value for the pending field: answer it if it is a real question, then ask again
      const cls = classify(norm);
      if (cls !== 'unknown' && !['ready_to_book', 'ready_to_book_soft', 'human', 'greeting'].includes(cls)) {
        const ans = answerIntent(agency, session, cls, lang, pkgMention);
        parts.push(ans);
      }
      parts.push(field === 'phone' && session.phoneTries > 0 ? ASK.phoneAgain(agency, lang) : ASK[field](agency, lang));
      return { text: parts.join('\n\n'), intent: 'collecting', lang, handoff: null };
    }

    intent = classify(norm);
    if (pkgMention && !['complaint', 'negotiation'].includes(intent)) session.lead.package = session.lead.package || pkgMention.id;

    if (intent === 'unknown') {
      session.unknownRun += 1;
      if (session.unknownRun >= 2) {
        startHandoff(session, 'unknown_repeated');
        parts.push(T(lang, {
          ar: 'يبدو أن سؤالك يحتاج صاحب الوكالة. أسجّل لك طلب اتصال.', dz: 'باين سؤالك يحتاج صاحب الوكالة. نسجّل لك طلب اتصال.',
          fr: 'Votre question demande plutôt le responsable. Je note une demande de rappel.'
        }));
        parts.push(ASK[nextMissing(session)](agency, lang));
        session.unknownRun = 0;
        return { text: parts.join('\n\n'), intent: 'handoff_start', lang, handoff: null };
      }
      parts.push(R.fallback(agency, lang));
      return { text: parts.join('\n\n'), intent, lang, handoff: null };
    }
    session.unknownRun = 0;

    if (['complaint', 'negotiation', 'human', 'religious', 'ready_to_book', 'ready_to_book_soft'].includes(intent)) {
      const reason = intent === 'ready_to_book_soft' ? 'ready_to_book' : (intent === 'religious' ? 'human_requested' : intent === 'human' ? 'human_requested' : intent);
      if (intent === 'complaint') {
        parts.push(T(lang, { ar: 'أعتذر عن هذا. الشكاوى لا أعالجها آلياً: سأحوّلها لصاحب الوكالة ليتكفل بها شخصياً.', dz: 'نعتذر على هادا. الشكاوى ما نعالجهاش آلياً: نوصّلها لصاحب الوكالة باش يتكفل بيها بنفسه.', fr: "Je suis désolé. Je ne traite pas les réclamations moi-même : je les transmets au responsable qui s'en occupera personnellement." }));
      } else if (intent === 'negotiation') {
        parts.push(T(lang, {
          ar: 'فهمت. أنا لا أملك صلاحية تغيير الأسعار أو التخفيض، وهذا يقرره صاحب الوكالة وحده. الباقة الاقتصادية هي الأقل سعراً (' + money(agency.packages[0].price_dzd, lang, agency) + '). إذا أحببت أسجّل لك طلب اتصال لمناقشة العرض.',
          dz: 'فهمتك. ما عنديش صلاحية نبدل الأسعار ولا ننقص، هادي يقررها صاحب الوكالة وحده. الباقة الاقتصادية هي الأرخص (' + money(agency.packages[0].price_dzd, lang, agency) + '). إذا حبيت نسجّل لك طلب اتصال باش تهدرو على العرض.',
          fr: "Je comprends. Je n'ai pas le pouvoir de modifier les prix ni de faire une remise : seul le responsable décide. La formule Économique est la moins chère (" + money(agency.packages[0].price_dzd, lang, agency) + "). Si vous voulez, je note une demande de rappel pour en discuter."
        }));
        // the offer above is a question: wait for the customer's yes before collecting details
        session.pendingOffer = { reason: 'negotiation' };
        return { text: parts.join('\n\n'), intent, lang, handoff: null };
      } else if (intent === 'religious') {
        parts.push(R.religious(agency, lang));
        session.pendingOffer = { reason: 'human_requested' };
        return { text: parts.join('\n\n'), intent, lang, handoff: null };
      } else if (intent === 'human') {
        parts.push(T(lang, { ar: 'طبعاً. سأسجّل طلب اتصال وسيتصل بك صاحب الوكالة. (هاتف الوكالة: ' + agency.phone + ')', dz: 'أكيد. نسجّل طلب اتصال وصاحب الوكالة يتصل بيك. (تيليفون الوكالة: ' + agency.phone + ')', fr: 'Bien sûr. Je note une demande de rappel et le responsable vous contactera. (Téléphone de l\'agence : ' + agency.phone + ')' }));
      }
      startHandoff(session, reason);
      if (session.lead.package && reason === 'ready_to_book') { /* package already known from earlier turns */ }
      const missing = nextMissing(session);
      parts.push(ASK[missing](agency, lang));
      return { text: parts.join('\n\n'), intent: reason === 'ready_to_book' ? 'handoff_start' : intent, lang, handoff: null };
    }

    parts.push(answerIntent(agency, session, intent, lang, pkgMention));
    return { text: parts.join('\n\n'), intent, lang, handoff: null };
  }

  function answerIntent(agency, session, intent, lang, pkg) {
    const p = pkg || (session.lead.package ? agency.packages.find((x) => x.id === session.lead.package) : null);
    switch (intent) {
      case 'price': return R.price(agency, lang, pkg);
      case 'dates': return R.dates(agency, lang, pkg);
      case 'documents': return R.documents(agency, lang);
      case 'visa': return R.visa(agency, lang);
      case 'includes': return R.includes(agency, lang, pkg);
      case 'duration': return R.duration(agency, lang);
      case 'payment': return R.payment(agency, lang);
      case 'booking_how': return R.booking_how(agency, lang);
      case 'packages': return R.packages(agency, lang);
      case 'thanks': return R.thanks(agency, lang);
      case 'bye': return R.bye(agency, lang);
      case 'greeting': return session.greeted && session.userLog.length > 1 ? R.menu(agency, lang) : R.menu(agency, lang);
      default: return p ? R.price(agency, lang, p) : R.fallback(agency, lang);
    }
  }

  // A "yes" after the assistant offered a call-back (negotiation / religious question).
  const YES_TOKENS = nkw(['نعم', 'اه', 'ايه', 'ايوه', 'اي', 'واه', 'يلا', 'ok', 'okay', 'oui', 'ouais', 'dac', 'wah', 'iyeh', 'ih', 'ey', 'sah', 'volontiers', 'ouii', 'yes']);
  const YES_PHRASES = nkw(['d accord', 'bien sur', 'si vous voulez']);
  function wantsCallback(text) {
    const norm = normalize(text);
    const toks = norm.split(' ');
    return toks.length <= 6 && (toks.some((t) => YES_TOKENS.includes(t)) || YES_PHRASES.some((ph) => norm.includes(ph)));
  }

  return { normalize, detectLang, classify: (t) => classify(normalize(t)), respond, newSession, wantsCallback, parsePhone, parsePersons, startHandoff, nextMissing, ASK };
});
