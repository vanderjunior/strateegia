import React, { useState, useEffect } from 'react';

// Constantes de estilo mapeadas a partir do CSS original do utilizador
const COLORS = {
  base: '#1a2f3f',     // petróleo médio — fundo principal
  s1: '#152738',       // um grau mais fundo
  s2: '#0f1e2a',       // naval escuro — superfícies elevadas
  s3: '#0a1520',       // naval mais profundo
  s4: '#2a4a61',       // naval claro — cards hover
  s5: '#243f55',       // cards repouso
  gold: '#c9a96e',     // dourado premium
  gold2: '#dfc08a',    // dourado hover
  gold3: 'rgba(201,169,110,0.14)',
  goldl: 'rgba(201,169,110,0.28)',
  silver: '#a8b8c4',
  silverl: 'rgba(168,184,196,0.18)',
  silverb: 'rgba(168,184,196,0.10)',
  t0: '#e8eef2',
  t1: 'rgba(232,238,242,0.75)',
  t2: 'rgba(232,238,242,0.45)',
  t3: 'rgba(232,238,242,0.25)',
  t4: 'rgba(232,238,242,0.12)',
  line: 'rgba(168,184,196,0.10)',
  line2: 'rgba(168,184,196,0.18)'
};

// Componente de Logo Inteligente, Criativo e Atemporal (Rosa dos Ventos com Grafo em M)
function MentoriumLogo({ className = "w-9 h-9" }) {
  return (
    <div className={`${className} transition-transform duration-500 hover:scale-105 transform-gpu flex-shrink-0`}>
      <svg viewBox="0 0 100 100" className="w-full h-full" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Órbitas / Círculos de Mapeamento de Fundo */}
        <circle cx="50" cy="50" r="44" stroke={COLORS.line2} strokeWidth="1" strokeDasharray="3 3" />
        <circle cx="50" cy="50" r="32" stroke={COLORS.goldl} strokeWidth="1" opacity="0.4" />
        
        {/* Linhas de Eixos da Bússola (Direcionamento) */}
        <line x1="50" y1="12" x2="50" y2="88" stroke={COLORS.line2} strokeWidth="1" />
        <line x1="12" y1="50" x2="88" y2="50" stroke={COLORS.line2} strokeWidth="1" />
        
        {/* Agulha da Bússola (Elegante e sutil, atrás do M) */}
        <path d="M50 15 L53.5 50 L50 85 L46.5 50 Z" fill={COLORS.s4} opacity="0.3" />
        <path d="M50 15 L50 50 L46.5 50 Z" fill={COLORS.silver} opacity="0.2" />

        {/* Marcador do Norte (Seta superior da Rosa dos Ventos) */}
        <path d="M50 8 L54 18 L46 18 Z" fill={COLORS.gold} />

        {/* CONEXÃO DO GRAFO EM "M" PARA BAIXO (Golden knowledge graph)
          Vértices do M:
          A: (28, 68) - Base esquerda
          B: (28, 30) - Topo esquerdo
          C: (50, 54) - Vértice do meio (aponta para baixo, no coração da bússola)
          D: (72, 30) - Topo direito
          E: (72, 68) - Base direita
        */}
        <path 
          d="M28 68 L28 30 L50 54 L72 30 L72 68" 
          stroke="url(#logoGoldGrad)" 
          strokeWidth="3" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
        />
        
        {/* Linhas de suporte do Grafo (Representando mapeamento de conteúdo) */}
        <line x1="28" y1="30" x2="50" y2="18" stroke={COLORS.silver} strokeWidth="1.2" strokeDasharray="2 2" opacity="0.6" />
        <line x1="72" y1="30" x2="50" y2="18" stroke={COLORS.silver} strokeWidth="1.2" strokeDasharray="2 2" opacity="0.6" />
        
        {/* Vértices / Nós brilhantes do Grafo */}
        {/* Topo Central Auxiliar */}
        <circle cx="50" cy="18" r="3.5" fill={COLORS.gold} />
        
        {/* Nós principais que formam o M */}
        <circle cx="28" cy="68" r="4.5" fill={COLORS.silver} stroke={COLORS.s2} strokeWidth="1.5" />
        <circle cx="28" cy="30" r="5" fill={COLORS.gold2} stroke={COLORS.s2} strokeWidth="1.5" />
        <circle cx="50" cy="54" r="6" fill={COLORS.gold} stroke={COLORS.s2} strokeWidth="1.5" className="animate-pulse" />
        <circle cx="72" cy="30" r="5" fill={COLORS.gold2} stroke={COLORS.s2} strokeWidth="1.5" />
        <circle cx="72" cy="68" r="4.5" fill={COLORS.silver} stroke={COLORS.s2} strokeWidth="1.5" />
        
        {/* Gradiente de Dourado Premium para as linhas do M */}
        <defs>
          <linearGradient id="logoGoldGrad" x1="28" y1="30" x2="72" y2="68" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor={COLORS.gold2} />
            <stop offset="50%" stopColor={COLORS.gold} />
            <stop offset="100%" stopColor={COLORS.gold2} />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

const INITIAL_TOPICS = [
  { id: 1, name: 'Princípios Fundamentais', progress: 88, status: 'ok' },
  { id: 2, name: 'Direitos e Garantias Individuais', progress: 72, status: 'ok' },
  { id: 3, name: 'Organização do Estado', progress: 41, status: 'warning' },
  { id: 4, name: 'Poder Executivo e Atribuições', progress: 28, status: 'warning' },
  { id: 5, name: 'Controlo de Constitucionalidade', progress: 15, status: 'critical' }
];

export default function App() {
  const [user, setUser] = useState(null); 
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTab, setModalTab] = useState('login'); 
  const [currentSection, setCurrentSection] = useState('home'); 
  
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPass, setRegisterPass] = useState('');

  const [topics, setTopics] = useState(INITIAL_TOPICS);
  const [materials, setMaterials] = useState([
    { id: 1, name: 'Constituição_Federal_1988.pdf', size: '4.2 MB', date: 'Há 2 dias', type: 'PDF' },
    { id: 2, name: 'Doutrina_Direito_Constitucional.md', size: '840 KB', date: 'Há 5 horas', type: 'Markdown' }
  ]);
  const [editais, setEditais] = useState([
    { id: 1, name: 'Edital_Senado_Federal_2026.pdf', date: 'Há 1 dia', status: 'Processado' }
  ]);
  
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [questionFeedback, setQuestionFeedback] = useState(null);
  const [studyStreak, setStudyStreak] = useState(4); 
  const [sessionScore, setSessionScore] = useState(0);

  const QUESTIONS = [
    {
      id: 1,
      subject: 'Direito Constitucional - Organização do Estado',
      text: 'Relativamente à organização político-administrativa da República Federativa do Brasil, a criação de Territórios Federais integra a organização administrativa da União, dependendo de lei complementar para a sua instituição física.',
      options: [
        { id: 'C', text: 'Certo - Conforme artigo 18, § 2º da CF/88.' },
        { id: 'E', text: 'Errado - Não necessita de lei complementar.' }
      ],
      correct: 'C',
      targetTopicId: 3 
    },
    {
      id: 2,
      subject: 'Direito Constitucional - Poder Executivo',
      text: 'Na vigência do mandato, o Presidente da República não pode ser responsabilizado por atos estranhos ao exercício de suas funções governamentais.',
      options: [
        { id: 'C', text: 'Certo - Trata-se da imunidade temporária prevista no art. 86, § 4º.' },
        { id: 'E', text: 'Errado - Pode ser responsabilizado civil e criminalmente por qualquer ato.' }
      ],
      correct: 'C',
      targetTopicId: 4 
    }
  ];

  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    if (loginEmail && loginPass) {
      setUser({
        name: loginEmail.split('@')[0],
        email: loginEmail
      });
      setModalOpen(false);
      setCurrentSection('overview');
    }
  };

  const handleRegister = (e) => {
    e.preventDefault();
    if (registerName && registerEmail && registerPass) {
      setUser({
        name: registerName,
        email: registerEmail
      });
      setModalOpen(false);
      setCurrentSection('overview');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentSection('home');
  };

  const handleAnswerSubmit = (optionId) => {
    if (selectedAnswer !== null) return;
    setSelectedAnswer(optionId);
    const question = QUESTIONS[currentQuestionIdx];
    const isCorrect = optionId === question.correct;
    
    if (isCorrect) {
      setQuestionFeedback('correct');
      setSessionScore(prev => prev + 10);
      setTopics(prev => prev.map(t => {
        if (t.id === question.targetTopicId) {
          const nextProgress = Math.min(t.progress + 8, 100);
          return { ...t, progress: nextProgress, status: nextProgress > 50 ? 'ok' : 'warning' };
        }
        return t;
      }));
    } else {
      setQuestionFeedback('wrong');
      setTopics(prev => prev.map(t => {
        if (t.id === question.targetTopicId) {
          const nextProgress = Math.max(t.progress - 5, 0);
          return { ...t, progress: nextProgress, status: nextProgress < 40 ? 'critical' : 'warning' };
        }
        return t;
      }));
    }
  };

  const nextQuestion = () => {
    setSelectedAnswer(null);
    setQuestionFeedback(null);
    setCurrentQuestionIdx((prev) => (prev + 1) % QUESTIONS.length);
  };

  const handleSimulatedUpload = (type) => {
    if (type === 'edital') {
      const newEdital = {
        id: editais.length + 1,
        name: `Edital_Adicional_${Date.now().toString().slice(-4)}.pdf`,
        date: 'Agora mesmo',
        status: 'Processando'
      };
      setEditais([newEdital, ...editais]);
      setTimeout(() => {
        setEditais(prev => prev.map(e => e.id === newEdital.id ? { ...e, status: 'Mapeado e Pronto' } : e));
      }, 3000);
    } else {
      const newMaterial = {
        id: materials.length + 1,
        name: `Material_Auxiliar_${Date.now().toString().slice(-4)}.pdf`,
        size: '1.8 MB',
        date: 'Agora mesmo',
        type: 'PDF'
      };
      setMaterials([newMaterial, ...materials]);
    }
  };

  return (
    <div className="min-h-screen font-sans antialiased text-slate-100 flex flex-col justify-between" style={{ backgroundColor: COLORS.base }}>
      
      {/* CABEÇALHO / NAVBAR */}
      <nav className={`fixed top-0 left-0 right-0 z-40 h-16 flex items-center justify-between px-6 md:px-12 transition-all duration-300 ${scrolled ? 'bg-[#0f1e2a]/95 backdrop-blur-md border-b' : 'bg-transparent border-b border-transparent'}`} style={{ borderBottomColor: scrolled ? COLORS.line : 'transparent' }}>
        <div className="flex items-center gap-3 cursor-pointer group" onClick={() => user ? setCurrentSection('overview') : setCurrentSection('home')}>
          <MentoriumLogo className="w-8 h-8 group-hover:rotate-[15deg] transition-transform duration-300" />
          <span className="font-semibold text-lg tracking-tight text-white font-sans">Mentorium</span>
        </div>

        {/* Links do meio (só visíveis na landing page) */}
        {!user && (
          <div className="hidden md:flex items-center gap-8">
            <a href="#pipeline" className="text-xs transition-colors" style={{ color: COLORS.t2 }}>Pipeline</a>
            <a href="#features" className="text-xs transition-colors" style={{ color: COLORS.t2 }}>Funcionalidades</a>
            <a href="#how" className="text-xs transition-colors" style={{ color: COLORS.t2 }}>Como Funciona</a>
            <a href="#pricing" className="text-xs transition-colors" style={{ color: COLORS.t2 }}>Planos</a>
          </div>
        )}

        {/* Links da direita */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-4">
              <span className="hidden sm:inline-block text-xs" style={{ color: COLORS.t2 }}>Olá, <strong className="text-white font-medium">{user.name}</strong></span>
              <button 
                onClick={handleLogout} 
                className="px-4 py-1.5 rounded-lg text-xs font-medium border transition-all" 
                style={{ borderColor: COLORS.line2, color: COLORS.t1 }}
              >
                Sair
              </button>
            </div>
          ) : (
            <>
              <button 
                onClick={() => { setModalTab('login'); setModalOpen(true); }} 
                className="px-4 py-1.5 rounded-lg text-xs font-medium border transition-all" 
                style={{ borderColor: COLORS.line2, color: COLORS.t2 }}
              >
                Entrar
              </button>
              <button 
                onClick={() => { setModalTab('signup'); setModalOpen(true); }} 
                className="px-4 py-1.5 rounded-lg text-xs font-bold transition-all transform hover:-translate-y-0.5" 
                style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}
              >
                Criar Conta
              </button>
            </>
          )}
        </div>
      </nav>

      {/* ÁREA PRINCIPAL DA APLICAÇÃO */}
      <main className="flex-1 pt-16">
        
        {/* VIEW 1: LANDING PAGE (Sessão não iniciada) */}
        {!user && (
          <div>
            
            {/* HERO SECTION */}
            <section className="relative min-h-screen flex flex-col items-center justify-center px-6 text-center overflow-hidden py-24">
              <div className="absolute inset-0 pointer-events-none" style={{
                backgroundImage: `radial-gradient(ellipse 70% 55% at 50% -5%, rgba(201,169,110,0.09) 0%, transparent 65%)`
              }}></div>
              <div className="absolute inset-0 pointer-events-none opacity-20" style={{
                backgroundImage: `radial-gradient(${COLORS.silver} 1px, transparent 1px)`,
                backgroundSize: '36px 36px'
              }}></div>

              {/* Novo Logo em destaque no Hero */}
              <div className="flex justify-center mb-6">
                <div className="p-4 rounded-full border bg-[#0a1520]/60 backdrop-blur transition-all duration-500 hover:rotate-6" style={{ borderColor: COLORS.goldl }}>
                  <MentoriumLogo className="w-16 h-16" />
                </div>
              </div>

              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border mb-8 animate-fade-in" style={{ backgroundColor: COLORS.gold3, borderColor: COLORS.goldl }}>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
                <span className="font-mono text-[10px] tracking-wider uppercase" style={{ color: COLORS.gold }}>plataforma edital-aware · acesso antecipado</span>
              </div>

              <h1 className="font-serif text-5xl md:text-8xl font-light leading-[1.05] tracking-tight mb-6">
                Estude o que <br />
                <em className="font-bold italic" style={{ color: COLORS.gold }}>vai cair.</em><br />
                <span className="block text-transparent stroke-text" style={{ WebkitTextStroke: `1px ${COLORS.t4}` }}>Nada além.</span>
              </h1>

              <p className="max-w-xl mx-auto text-base md:text-lg font-light leading-relaxed mb-10" style={{ color: COLORS.t2 }}>
                O Mentorium lê o seu edital, alinha a sua bibliografia e monta um plano de estudos cirúrgico. 
                Depois guia-o com resumos, questões e simulados adaptados ao seu desempenho em tempo real.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16 w-full max-w-md">
                <button 
                  onClick={() => { setModalTab('signup'); setModalOpen(true); }} 
                  className="px-8 py-3.5 rounded-xl text-sm font-bold shadow-lg transition-all duration-300 transform hover:-translate-y-1 hover:shadow-amber-500/10" 
                  style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}
                >
                  Criar conta gratuita
                </button>
                <a 
                  href="#how" 
                  className="px-8 py-3.5 rounded-xl text-sm font-medium border text-center transition-all duration-300" 
                  style={{ borderColor: COLORS.line2, color: COLORS.t1 }}
                >
                  Como funciona
                </a>
              </div>

              {/* MOCKUP INTERATIVO DA PLATAFORMA */}
              <div className="w-full max-w-4xl rounded-2xl overflow-hidden border shadow-2xl" style={{ borderColor: COLORS.line, backgroundColor: COLORS.s2 }}>
                <div className="h-10 flex items-center justify-between px-4 border-b" style={{ backgroundColor: COLORS.s3, borderColor: COLORS.line }}>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                  </div>
                  <div className="px-12 py-1 rounded bg-[#ffffff0a] border font-mono text-[10px]" style={{ borderColor: COLORS.line, color: COLORS.t3 }}>
                    app.mentorium.com.br/dashboard
                  </div>
                  <div className="w-6"></div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] min-h-[340px]">
                  {/* Lateral mockup */}
                  <div className="hidden md:block border-r p-5 text-left" style={{ backgroundColor: COLORS.s3, borderColor: COLORS.line }}>
                    <div className="font-mono text-[9px] tracking-widest text-slate-500 uppercase mb-4">Painel</div>
                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold mb-1" style={{ backgroundColor: COLORS.gold3, color: COLORS.gold }}>
                      <span>📊</span> Sessão adaptativa
                    </div>
                    {['📋 Edital', '📄 Materiais', '🔄 Ciclo', '✅ Simulados'].map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs mb-1" style={{ color: COLORS.t2 }}>
                        {item}
                      </div>
                    ))}
                  </div>

                  {/* Corpo mockup */}
                  <div className="p-6 text-left flex flex-col justify-between gap-6">
                    <div>
                      <div className="font-mono text-[9px] tracking-wider uppercase mb-3" style={{ color: COLORS.silver }}>retenção imediata · Direito Constitucional</div>
                      <div className="space-y-3">
                        {topics.slice(0, 4).map((topic) => (
                          <div key={topic.id} className="flex items-center justify-between gap-4 border-b py-2" style={{ borderColor: COLORS.line }}>
                            <span className="text-xs font-light" style={{ color: COLORS.t1 }}>{topic.name}</span>
                            <div className="flex items-center gap-3">
                              <div className="w-24 h-1.5 bg-[#ffffff0c] rounded-full overflow-hidden">
                                <div 
                                  className="h-full rounded-full transition-all duration-1000" 
                                  style={{ 
                                    width: `${topic.progress}%`, 
                                    backgroundColor: topic.status === 'ok' ? COLORS.silver : '#ef4444' 
                                  }}
                                ></div>
                              </div>
                              <span className="font-mono text-[11px] font-semibold w-8 text-right" style={{ color: topic.status === 'ok' ? COLORS.silver : '#f87171' }}>{topic.progress}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 rounded-lg border text-left" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                        <div className="font-mono text-[8px] tracking-wider text-slate-400 uppercase mb-1">Retenção geral</div>
                        <div className="text-2xl font-serif font-bold text-white">67%</div>
                        <div className="text-[10px] mt-1" style={{ color: COLORS.gold }}>↑ +12% esta semana</div>
                      </div>
                      <div className="p-3 rounded-lg border text-left" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                        <div className="font-mono text-[8px] tracking-wider text-slate-400 uppercase mb-1">Tópicos cobertos</div>
                        <div className="text-2xl font-serif font-bold text-white">6 / 8</div>
                        <div className="text-[10px] text-slate-400 mt-1">alinhados ao edital</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* PIPELINE DE CONHECIMENTO */}
            <section id="pipeline" className="py-24 border-t border-b" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
              <div className="max-w-6xl mx-auto px-6">
                <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-12 items-start">
                  <div>
                    <span className="inline-flex items-center gap-2 font-mono text-[10px] tracking-widest text-slate-400 uppercase mb-4">
                      <span className="w-4 h-[1px] bg-slate-500"></span> pipeline de conhecimento
                    </span>
                    <h2 className="font-serif text-4xl md:text-6xl font-light leading-none tracking-tight mb-6">
                      Do upload ao <em className="font-bold italic" style={{ color: COLORS.gold }}>simulado</em>,<br />
                      <span className="opacity-40">automatizado.</span>
                    </h2>
                    <p className="font-light leading-relaxed mb-8" style={{ color: COLORS.t2 }}>
                      Uma cadeia determinística e auditável que transforma os seus materiais reais de estudo num plano curricular dinâmico.
                    </p>
                    <div className="flex gap-2 flex-wrap">
                      <span className="px-3 py-1 rounded border text-[10px] font-mono" style={{ borderColor: 'rgba(100,200,140,0.2)', color: 'rgba(140,220,160,0.75)', backgroundColor: 'rgba(100,200,140,0.05)' }}>ativo</span>
                      <span className="px-3 py-1 rounded border text-[10px] font-mono" style={{ borderColor: COLORS.line2, color: COLORS.silver }}>em desenvolvimento</span>
                      <span className="px-3 py-1 rounded border text-[10px] font-mono" style={{ borderColor: COLORS.goldl, color: COLORS.gold }}>planeado</span>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div className="flex gap-4 items-start p-4 rounded-xl transition-all duration-300 hover:bg-[#ffffff03]">
                      <div className="w-8 h-8 rounded-full border flex items-center justify-center text-xs flex-shrink-0" style={{ borderColor: COLORS.goldl, backgroundColor: COLORS.gold3, color: COLORS.gold }}>01</div>
                      <div>
                        <h4 className="font-semibold text-sm mb-1 text-white">Upload de Materiais</h4>
                        <p className="text-xs font-light leading-relaxed" style={{ color: COLORS.t2 }}>Suporta PDFs de livros, apostilas, anotações de aula e fichários — processados de forma privada.</p>
                      </div>
                    </div>
                    <div className="flex gap-4 items-start p-4 rounded-xl transition-all duration-300 hover:bg-[#ffffff03]">
                      <div className="w-8 h-8 rounded-full border flex items-center justify-center text-xs flex-shrink-0" style={{ borderColor: COLORS.goldl, backgroundColor: COLORS.gold3, color: COLORS.gold }}>02</div>
                      <div>
                        <h4 className="font-semibold text-sm mb-1 text-white">Segmentação Documental</h4>
                        <p className="text-xs font-light leading-relaxed" style={{ color: COLORS.t2 }}>Extração de metadados, leitura hierárquica e armazenamento estruturado para guiar a IA de forma contextualizada.</p>
                      </div>
                    </div>
                    <div className="flex gap-4 items-start p-4 rounded-xl transition-all duration-300 hover:bg-[#ffffff03]">
                      <div className="w-8 h-8 rounded-full border flex items-center justify-center text-xs flex-shrink-0" style={{ borderColor: COLORS.goldl, backgroundColor: COLORS.gold3, color: COLORS.gold }}>03</div>
                      <div>
                        <h4 className="font-semibold text-sm mb-1 text-white">Ingestão Dinâmica de Editais</h4>
                        <p className="text-xs font-light leading-relaxed" style={{ color: COLORS.t2 }}>Deteção de conteúdo programático, peso das disciplinas e datas-limite para focar unicamente nas metas reais.</p>
                      </div>
                    </div>
                    <div className="flex gap-4 items-start p-4 rounded-xl transition-all duration-300 hover:bg-[#ffffff03]">
                      <div className="w-8 h-8 rounded-full border flex items-center justify-center text-xs flex-shrink-0" style={{ borderColor: COLORS.goldl, backgroundColor: COLORS.gold3, color: COLORS.gold }}>04</div>
                      <div>
                        <h4 className="font-semibold text-sm mb-1 text-white">Alinhamento & Gaps</h4>
                        <p className="text-xs font-light leading-relaxed" style={{ color: COLORS.t2 }}>O sistema cruza as matérias exigidas com a sua biblioteca de uploads e alerta instantaneamente sobre tópicos que não possui em arquivo.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* FUNCIONALIDADES */}
            <section id="features" className="py-24">
              <div className="max-w-6xl mx-auto px-6">
                <div className="text-center max-w-xl mx-auto mb-16">
                  <span className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">Funcionalidades do Ecossistema</span>
                  <h2 className="font-serif text-3xl md:text-5xl font-light mt-3">Tudo o que precisa para ser <em className="font-bold italic" style={{ color: COLORS.gold }}>aprovado.</em></h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    { icon: '📄', title: 'Upload Avançado', desc: 'Arraste livros completos e apostilas. Segmentamos o conteúdo automaticamente por capítulos.' },
                    { icon: '📋', title: 'Leitura de Editais', desc: 'Upload do edital oficial em PDF. O Mentorium analisa as regras e ponderações da banca examinadora.' },
                    { icon: '🔗', title: 'Mapeamento Bibliográfico', desc: 'Saiba com precisão quais as páginas do seu material respondem a cada linha do edital.' },
                    { icon: '🧠', title: 'Tutor Inteligente', desc: 'Explicações detalhadas baseadas exclusivamente no seu material oficial, evitando alucinações.' },
                    { icon: '🔄', title: 'Rotação de Ciclos', desc: 'Um algoritmo de distribuição de tempo focado na curva de esquecimento e complexidade do tópico.' },
                    { icon: '✅', title: 'Simulados de Banca', desc: 'Questões no estilo da banca (CEBRASPE, FGV) criadas sob medida a partir dos seus PDFs.' }
                  ].map((feat, i) => (
                    <div key={i} className="p-8 rounded-xl border text-left transition-all duration-300 hover:scale-[1.02]" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <div className="text-3xl mb-4">{feat.icon}</div>
                      <h3 className="font-serif text-xl font-semibold text-white mb-2">{feat.title}</h3>
                      <p className="text-xs font-light leading-relaxed" style={{ color: COLORS.t2 }}>{feat.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* PLANOS */}
            <section id="pricing" className="py-24 border-t" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
              <div className="max-w-5xl mx-auto px-6 text-center">
                <span className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">Planos de Acesso</span>
                <h2 className="font-serif text-3xl md:text-5xl font-light mt-3 mb-16">Simples. <em className="font-bold italic" style={{ color: COLORS.gold }}>Transparente.</em></h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <div className="p-8 rounded-xl border text-left flex flex-col justify-between" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                    <div>
                      <div className="font-mono text-[10px] tracking-wider text-slate-400 uppercase mb-4">// Gratuito</div>
                      <div className="text-4xl font-serif font-light text-white mb-6">R$ 0 <span className="text-xs text-slate-500">/mês</span></div>
                      <p className="text-xs font-light text-slate-400 mb-6">Ideal para conhecer o fluxo de mapeamento e organizar os seus resumos.</p>
                      <ul className="space-y-3 text-xs font-light text-slate-300 mb-8">
                        <li>✓ 3 materiais de estudo</li>
                        <li>✓ Leitura de 1 edital</li>
                        <li>✓ Pipeline básico</li>
                      </ul>
                    </div>
                    <button onClick={() => { setModalTab('signup'); setModalOpen(true); }} className="w-full py-2.5 rounded-lg text-xs font-semibold border transition-all" style={{ borderColor: COLORS.line2, color: COLORS.t1 }}>Começar Grátis</button>
                  </div>

                  <div className="p-8 rounded-xl border text-left flex flex-col justify-between relative" style={{ backgroundColor: COLORS.s3, borderColor: COLORS.gold }}>
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[9px] font-mono tracking-widest uppercase" style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}>Acesso Antecipado</div>
                    <div>
                      <div className="font-mono text-[10px] tracking-wider text-slate-400 uppercase mb-4 mt-2">// Profissional</div>
                      <div className="text-xl font-mono text-slate-400 mb-6 py-2">a definir</div>
                      <p className="text-xs font-light text-slate-400 mb-6">Completo. Membros pioneiros terão descontos perpétuos no lançamento.</p>
                      <ul className="space-y-3 text-xs font-light text-slate-300 mb-8">
                        <li>✓ Uploads ilimitados de PDFs</li>
                        <li>✓ Alinhamento automático</li>
                        <li>✓ Tutor adaptativo de IA</li>
                        <li>✓ Simulados ilimitados</li>
                      </ul>
                    </div>
                    <button onClick={() => { setModalTab('signup'); setModalOpen(true); }} className="w-full py-2.5 rounded-lg text-xs font-bold transition-all" style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}>Entrar na Lista</button>
                  </div>

                  <div className="p-8 rounded-xl border text-left flex flex-col justify-between" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                    <div>
                      <div className="font-mono text-[10px] tracking-wider text-slate-400 uppercase mb-4">// Reta Final</div>
                      <div className="text-xl font-mono text-slate-400 mb-6 py-2">a definir</div>
                      <p className="text-xs font-light text-slate-400 mb-6">Para quem tem provas marcadas para os próximos 60 dias.</p>
                      <ul className="space-y-3 text-xs font-light text-slate-300 mb-8">
                        <li>✓ Resumão pré-prova adaptado</li>
                        <li>✓ Diagnóstico avançado de lacunas</li>
                        <li>✓ Suporte VIP prioritário</li>
                      </ul>
                    </div>
                    <button onClick={() => { setModalTab('signup'); setModalOpen(true); }} className="w-full py-2.5 rounded-lg text-xs font-semibold border transition-all" style={{ borderColor: COLORS.line2, color: COLORS.t1 }}>Saber Mais</button>
                  </div>
                </div>
              </div>
            </section>

          </div>
        )}

        {/* VIEW 2: ÁREA LOGADA / DASHBOARD */}
        {user && (
          <div className="max-w-7xl mx-auto px-6 py-8 animate-fade-in">
            <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-8">
              
              {/* SIDEBAR DO DASHBOARD */}
              <aside className="space-y-6">
                <div className="p-5 rounded-2xl border text-left" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                  <div className="font-mono text-[10px] tracking-wider text-slate-400 uppercase mb-4">Painel de Controlo</div>
                  <nav className="flex flex-col gap-1">
                    <button 
                      onClick={() => setCurrentSection('overview')}
                      className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${currentSection === 'overview' ? 'font-bold' : ''}`}
                      style={{ 
                        backgroundColor: currentSection === 'overview' ? COLORS.gold3 : 'transparent',
                        color: currentSection === 'overview' ? COLORS.gold : COLORS.t2
                      }}
                    >
                      <span>📊</span> Dashboard Geral
                    </button>
                    <button 
                      onClick={() => setCurrentSection('edital')}
                      className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${currentSection === 'edital' ? 'font-bold' : ''}`}
                      style={{ 
                        backgroundColor: currentSection === 'edital' ? COLORS.gold3 : 'transparent',
                        color: currentSection === 'edital' ? COLORS.gold : COLORS.t2
                      }}
                    >
                      <span>📋</span> Mapeamento de Edital
                    </button>
                    <button 
                      onClick={() => setCurrentSection('materials')}
                      className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${currentSection === 'materials' ? 'font-bold' : ''}`}
                      style={{ 
                        backgroundColor: currentSection === 'materials' ? COLORS.gold3 : 'transparent',
                        color: currentSection === 'materials' ? COLORS.gold : COLORS.t2
                      }}
                    >
                      <span>📄</span> Biblioteca de Materiais
                    </button>
                    <button 
                      onClick={() => setCurrentSection('simulado')}
                      className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${currentSection === 'simulado' ? 'font-bold' : ''}`}
                      style={{ 
                        backgroundColor: currentSection === 'simulado' ? COLORS.gold3 : 'transparent',
                        color: currentSection === 'simulado' ? COLORS.gold : COLORS.t2
                      }}
                    >
                      <span>✅</span> Sessão Adaptativa
                    </button>
                  </nav>
                </div>

                {/* KPI RÁPIDO */}
                <div className="p-5 rounded-2xl border text-left space-y-4" style={{ backgroundColor: COLORS.s3, borderColor: COLORS.line }}>
                  <div className="font-mono text-[9px] tracking-wider text-slate-500 uppercase">Estado Geral</div>
                  <div className="flex justify-between items-center text-xs">
                    <span style={{ color: COLORS.t2 }}>Rendimento global</span>
                    <span className="font-bold text-emerald-400">76%</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span style={{ color: COLORS.t2 }}>Foco Semanal</span>
                    <span className="font-bold text-amber-300">12h</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span style={{ color: COLORS.t2 }}>Dias seguidos</span>
                    <span className="font-bold text-amber-500">🔥 {studyStreak} dias</span>
                  </div>
                </div>
              </aside>

              {/* SEÇÃO DINÂMICA DO DASHBOARD */}
              <section className="space-y-6">
                
                {/* 1. OVERVIEW / SESSÃO ATUAL */}
                {currentSection === 'overview' && (
                  <div className="space-y-6 text-left">
                    
                    {/* Mensagem de Boas-vindas */}
                    <div className="p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <h2 className="font-serif text-2xl md:text-3xl font-light mb-2">
                        Bem-vindo de volta, <em className="font-bold italic" style={{ color: COLORS.gold }}>{user.name}</em>
                      </h2>
                      <p className="text-xs font-light" style={{ color: COLORS.t2 }}>
                        A sua próxima matéria programada é <strong className="text-white font-medium">Direito Constitucional</strong>. O tutor sugere focar em <strong className="text-amber-300 font-medium">Organização do Estado</strong> para elevar a sua percentagem de retenção de 41% para 70%.
                      </p>
                      <button 
                        onClick={() => setCurrentSection('simulado')}
                        className="mt-4 px-5 py-2 rounded-lg text-xs font-bold transition-all"
                        style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}
                      >
                        Iniciar Sessão de Estudos
                      </button>
                    </div>

                    {/* Gráfico de Retenção Ativo */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      
                      {/* Retenção de Microtópicos */}
                      <div className="md:col-span-2 p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                        <div className="flex justify-between items-center mb-6">
                          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Mapeamento de Retenção por Tópico</span>
                          <span className="text-xs text-amber-400 font-medium">Requer atenção</span>
                        </div>
                        <div className="space-y-4">
                          {topics.map(topic => (
                            <div key={topic.id} className="space-y-1">
                              <div className="flex justify-between text-xs font-light">
                                <span style={{ color: COLORS.t1 }}>{topic.name}</span>
                                <span className="font-mono font-bold" style={{ color: topic.progress > 60 ? COLORS.silver : '#ef4444' }}>{topic.progress}%</span>
                              </div>
                              <div className="h-2 bg-[#ffffff0a] rounded-full overflow-hidden">
                                <div 
                                  className="h-full rounded-full transition-all duration-500" 
                                  style={{ 
                                    width: `${topic.progress}%`, 
                                    backgroundColor: topic.progress > 70 ? COLORS.gold : topic.progress > 40 ? '#f59e0b' : '#ef4444'
                                  }}
                                ></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Resumo da Próxima Prova */}
                      <div className="p-6 rounded-2xl border flex flex-col justify-between" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                        <div>
                          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase mb-4 block">Próximo Alvo</span>
                          <div className="text-xs text-slate-400 font-mono mb-2">CONCURSO ALINHADO:</div>
                          <div className="text-lg font-serif font-bold text-white mb-4">Tribunal Regional Federal</div>
                          
                          <div className="space-y-3">
                            <div className="p-3 rounded-lg border text-left text-xs space-y-1" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                              <div className="text-slate-400">Total de tópicos mapeados</div>
                              <div className="font-bold text-white text-base">45 microtópicos</div>
                            </div>
                            <div className="p-3 rounded-lg border text-left text-xs space-y-1" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                              <div className="text-slate-400">Materiais associados</div>
                              <div className="font-bold text-white text-base">2 PDF's ativos</div>
                            </div>
                          </div>
                        </div>
                        
                        <button 
                          onClick={() => setCurrentSection('edital')}
                          className="w-full mt-4 py-2 rounded-lg text-xs border transition-all"
                          style={{ borderColor: COLORS.line2, color: COLORS.t1 }}
                        >
                          Verificar Edital Completo
                        </button>
                      </div>

                    </div>

                    {/* Atividades recentes */}
                    <div className="p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase mb-4 block">Histórico de Atividade</span>
                      <div className="space-y-4">
                        <div className="flex justify-between items-center text-xs pb-3 border-b" style={{ borderColor: COLORS.line }}>
                          <div className="flex gap-3">
                            <span>✅</span>
                            <div>
                              <p className="font-semibold text-white">Sessão "Organização do Estado" terminada</p>
                              <p className="text-[10px] text-slate-400">Rendimento de 88%</p>
                            </div>
                          </div>
                          <span className="text-slate-500">Há 2 horas</span>
                        </div>
                        <div className="flex justify-between items-center text-xs pb-3 border-b" style={{ borderColor: COLORS.line }}>
                          <div className="flex gap-3">
                            <span>📄</span>
                            <div>
                              <p className="font-semibold text-white">Upload de "Constituição_Federal_1988.pdf"</p>
                              <p className="text-[10px] text-slate-400">Análise concluída com sucesso</p>
                            </div>
                          </div>
                          <span className="text-slate-500">Há 1 dia</span>
                        </div>
                      </div>
                    </div>

                  </div>
                )}

                {/* 2. MAPEADOR DE EDITAL */}
                {currentSection === 'edital' && (
                  <div className="space-y-6 text-left">
                    <div className="p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <h2 className="font-serif text-2xl font-light mb-2">Mapeamento Dinâmico de Edital</h2>
                      <p className="text-xs font-light text-slate-400 mb-6">
                        Faça o upload do documento oficial de vagas e cronograma. A nossa IA segmentará as matérias de interesse e cruzará os dados com os seus uploads bibliográficos.
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Área de Dropzone Simulada */}
                        <div 
                          onClick={() => handleSimulatedUpload('edital')}
                          className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all hover:bg-[#ffffff03]"
                          style={{ borderColor: COLORS.line2 }}
                        >
                          <div className="text-3xl mb-3">📋</div>
                          <h4 className="text-xs font-semibold text-white mb-1">Arraste o seu Edital oficial aqui</h4>
                          <p className="text-[10px] text-slate-500 mb-4">Aceita PDF, TXT ou DOC até 15MB</p>
                          <span className="px-3 py-1.5 rounded bg-amber-500/10 text-amber-300 text-[10px] font-bold">Simular Upload de Edital</span>
                        </div>

                        {/* Editais Atuais */}
                        <div className="space-y-3">
                          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Editais Mapeados</span>
                          {editais.map(e => (
                            <div key={e.id} className="p-4 rounded-xl border flex justify-between items-center" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                              <div>
                                <h4 className="text-xs font-semibold text-white">{e.name}</h4>
                                <span className="text-[10px] text-slate-500">{e.date}</span>
                              </div>
                              <span className={`text-[9px] font-mono font-bold px-2.5 py-1 rounded-full ${e.status === 'Processando' ? 'bg-amber-400/10 text-amber-400 animate-pulse' : 'bg-emerald-400/10 text-emerald-400'}`}>
                                {e.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase block mb-4">Alinhamento Programático Automático</span>
                      <p className="text-xs text-slate-400 mb-4">
                        O Mentorium encontrou <strong className="text-white font-medium">8 microtópicos ativos</strong>. Destes, <strong className="text-amber-300 font-medium">2 necessitam de materiais adicionais</strong> para cobrir a ementa completa:
                      </p>
                      <div className="space-y-2">
                        <div className="p-3 rounded-lg border text-xs flex justify-between items-center" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                          <span className="text-slate-300">Organização Administrativa e Terceiro Setor</span>
                          <span className="text-xs text-rose-400">Nenhum livro de Direito Administrativo associado</span>
                        </div>
                        <div className="p-3 rounded-lg border text-xs flex justify-between items-center" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                          <span className="text-slate-300">Poder Judiciário e Súmulas Vinculantes</span>
                          <span className="text-xs text-amber-400">PDF de Direito Constitucional incompleto (falta Cap. 12)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. BIBLIOTECA DE MATERIAIS */}
                {currentSection === 'materials' && (
                  <div className="space-y-6 text-left">
                    <div className="p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <h2 className="font-serif text-2xl font-light mb-2">Biblioteca de Referências</h2>
                      <p className="text-xs font-light text-slate-400 mb-6">
                        Adicione apostilas, anotações de aulas e materiais em geral. O Mentorium utiliza estes ficheiros como base única para gerar resumos e questões, evitando falsas respostas.
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        {/* Área de Dropzone Simulada */}
                        <div 
                          onClick={() => handleSimulatedUpload('material')}
                          className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all hover:bg-[#ffffff03]"
                          style={{ borderColor: COLORS.line2 }}
                        >
                          <div className="text-3xl mb-3">📄</div>
                          <h4 className="text-xs font-semibold text-white mb-1">Arraste os seus ficheiros de estudo aqui</h4>
                          <p className="text-[10px] text-slate-500 mb-4">Aceita PDF, TXT ou Markdown até 40MB</p>
                          <span className="px-3 py-1.5 rounded bg-emerald-500/10 text-emerald-300 text-[10px] font-bold">Simular Upload de Apostila</span>
                        </div>

                        {/* Estatística de Armazenamento */}
                        <div className="p-4 rounded-xl border flex flex-col justify-between" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                          <div>
                            <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase mb-2 block">Capacidade total utilizada</span>
                            <div className="text-3xl font-serif font-bold text-white mb-2">5.0 MB <span className="text-xs text-slate-500">de 50 MB (Plano Gratuito)</span></div>
                          </div>
                          <div className="w-full h-1.5 bg-[#ffffff0c] rounded-full overflow-hidden">
                            <div className="h-full bg-amber-400 rounded-full" style={{ width: '10%' }}></div>
                          </div>
                        </div>
                      </div>

                      {/* Lista de Ficheiros */}
                      <div className="space-y-3">
                        <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase block">Ficheiros Ativos</span>
                        {materials.map(file => (
                          <div key={file.id} className="p-4 rounded-xl border flex justify-between items-center" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                            <div className="flex gap-3 items-center">
                              <span className="text-2xl">📄</span>
                              <div>
                                <h4 className="text-xs font-semibold text-white">{file.name}</h4>
                                <span className="text-[10px] text-slate-500">{file.size} · Carregado {file.date}</span>
                              </div>
                            </div>
                            <button 
                              onClick={() => setMaterials(prev => prev.filter(m => m.id !== file.id))}
                              className="text-xs text-slate-500 hover:text-rose-400 transition-colors p-2"
                            >
                              Eliminar
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. SESSÃO ADAPTATIVA (SIMULADOR DE QUESTÕES COM FEEDBACK) */}
                {currentSection === 'simulado' && (
                  <div className="space-y-6 text-left">
                    <div className="p-6 rounded-2xl border" style={{ backgroundColor: COLORS.s2, borderColor: COLORS.line }}>
                      <div className="flex justify-between items-center mb-6">
                        <div>
                          <span className="font-mono text-[9px] tracking-wider text-slate-400 uppercase">Sessão Adaptativa Ativa</span>
                          <h2 className="font-serif text-2xl font-light">Tutor de Fixação</h2>
                        </div>
                        <div className="px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-300">
                          Pontuação: {sessionScore} pts
                        </div>
                      </div>

                      <div className="p-4 rounded-xl border mb-6" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line }}>
                        <div className="flex justify-between text-[10px] text-slate-400 mb-2">
                          <span>MATÉRIA: {QUESTIONS[currentQuestionIdx].subject}</span>
                          <span>QUESTÃO {currentQuestionIdx + 1} DE {QUESTIONS.length}</span>
                        </div>
                        <p className="text-sm font-light text-slate-100 leading-relaxed">
                          {QUESTIONS[currentQuestionIdx].text}
                        </p>
                      </div>

                      <div className="space-y-3 mb-6">
                        {QUESTIONS[currentQuestionIdx].options.map((option) => {
                          const isSelected = selectedAnswer === option.id;
                          let btnStyle = { backgroundColor: COLORS.s1, borderColor: COLORS.line };
                          
                          if (isSelected) {
                            if (questionFeedback === 'correct') {
                              btnStyle = { backgroundColor: 'rgba(52,211,153,0.1)', borderColor: '#10b981' };
                            } else {
                              btnStyle = { backgroundColor: 'rgba(239,68,68,0.1)', borderColor: '#ef4444' };
                            }
                          }

                          return (
                            <button
                              key={option.id}
                              onClick={() => handleAnswerSubmit(option.id)}
                              className="w-full p-4 rounded-xl border text-left text-xs font-light transition-all flex gap-3 items-center"
                              style={btnStyle}
                            >
                              <span className="w-6 h-6 rounded-full border flex items-center justify-center font-bold text-[10px] flex-shrink-0" style={{ borderColor: COLORS.line2 }}>
                                {option.id}
                              </span>
                              <span className="text-slate-200">{option.text}</span>
                            </button>
                          );
                        })}
                      </div>

                      {/* Feedback Interativo */}
                      {questionFeedback && (
                        <div className="p-4 rounded-xl border mb-6 text-xs" style={{ 
                          backgroundColor: questionFeedback === 'correct' ? 'rgba(52,211,153,0.05)' : 'rgba(239,68,68,0.05)',
                          borderColor: questionFeedback === 'correct' ? '#10b981/30' : '#ef4444/30'
                        }}>
                          {questionFeedback === 'correct' ? (
                            <p className="text-emerald-400 font-semibold mb-1">✨ Excelente! Resposta Correta.</p>
                          ) : (
                            <p className="text-rose-400 font-semibold mb-1">⚠️ Resposta Incorreta.</p>
                          )}
                          <p className="text-slate-400 font-light">
                            O seu índice de retenção para <strong className="text-white font-medium">{QUESTIONS[currentQuestionIdx].subject.split(' - ')[1]}</strong> foi ajustado. Continue para fixar a matéria na memória de longo prazo.
                          </p>
                        </div>
                      )}

                      <div className="flex justify-end">
                        <button
                          onClick={nextQuestion}
                          className="px-6 py-2.5 rounded-lg text-xs font-bold transition-all"
                          style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}
                        >
                          Próxima Questão
                        </button>
                      </div>
                    </div>
                  </div>
                )}

              </section>

            </div>
          </div>
        )}

      </main>

      {/* RODAPÉ / FOOTER */}
      <footer className="border-t py-12 px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-6" style={{ borderColor: COLORS.line }}>
        <div className="flex items-center gap-3">
          <MentoriumLogo className="w-8 h-8" />
          <span className="font-semibold text-sm tracking-tight text-white font-sans">Mentorium</span>
        </div>
        <p className="text-xs font-mono" style={{ color: COLORS.t3 }}>© 2026 Mentorium · Plataforma adaptativa de alta retenção.</p>
      </footer>

      {/* MODAL DE ENTRAR / CADASTRAR */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-lg px-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border p-8 relative overflow-hidden" style={{ backgroundColor: COLORS.s1, borderColor: COLORS.line2 }}>
            
            <button 
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors p-2"
            >
              ✕
            </button>

            <div className="flex items-center gap-2 mb-6">
              <MentoriumLogo className="w-6 h-6" />
              <span className="font-bold text-sm text-white font-sans">Mentorium</span>
            </div>

            {/* Abas */}
            <div className="flex gap-4 border-b mb-6" style={{ borderColor: COLORS.line }}>
              <button 
                onClick={() => setModalTab('login')} 
                className={`pb-2 text-xs font-medium transition-all border-b-2 ${modalTab === 'login' ? 'text-white border-amber-400' : 'text-slate-400 border-transparent'}`}
              >
                Entrar
              </button>
              <button 
                onClick={() => setModalTab('signup')} 
                className={`pb-2 text-xs font-medium transition-all border-b-2 ${modalTab === 'signup' ? 'text-white border-amber-400' : 'text-slate-400 border-transparent'}`}
              >
                Criar conta
              </button>
            </div>

            {modalTab === 'login' ? (
              <form onSubmit={handleLogin} className="space-y-4 text-left">
                <h3 className="font-serif text-xl font-bold text-white mb-1">Bem-vindo de volta.</h3>
                <p className="text-xs text-slate-400 mb-4">Continue os seus estudos de onde parou.</p>
                
                <div>
                  <label className="block text-[10px] font-mono tracking-wider text-slate-400 uppercase mb-1">E-mail de acesso</label>
                  <input 
                    type="email" 
                    required 
                    placeholder="exemplo@mentorium.com" 
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    className="w-full p-3 rounded-lg border text-xs text-white bg-[#0a1520] outline-none transition-all focus:border-amber-400"
                    style={{ borderColor: COLORS.line }}
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono tracking-wider text-slate-400 uppercase mb-1">Senha de segurança</label>
                  <input 
                    type="password" 
                    required 
                    placeholder="••••••••" 
                    value={loginPass}
                    onChange={(e) => setLoginPass(e.target.value)}
                    className="w-full p-3 rounded-lg border text-xs text-white bg-[#0a1520] outline-none transition-all focus:border-amber-400"
                    style={{ borderColor: COLORS.line }}
                  />
                  <div className="text-right mt-1">
                    <a href="#" className="text-[10px]" style={{ color: COLORS.gold }}>Esqueceu a senha?</a>
                  </div>
                </div>

                <button 
                  type="submit" 
                  className="w-full py-3 rounded-lg text-xs font-bold transition-all mt-2" 
                  style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}
                >
                  Entrar na Plataforma
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-4 text-left">
                <h3 className="font-serif text-xl font-bold text-white mb-1">Comece a sua jornada.</h3>
                <p className="text-xs text-slate-400 mb-4">Crie o seu acesso de estudos gratuito instantaneamente.</p>

                <div>
                  <label className="block text-[10px] font-mono tracking-wider text-slate-400 uppercase mb-1">Nome completo</label>
                  <input 
                    type="text" 
                    required 
                    placeholder="Como deseja ser chamado?" 
                    value={registerName}
                    onChange={(e) => setRegisterName(e.target.value)}
                    className="w-full p-3 rounded-lg border text-xs text-white bg-[#0a1520] outline-none transition-all focus:border-amber-400"
                    style={{ borderColor: COLORS.line }}
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono tracking-wider text-slate-400 uppercase mb-1">E-mail de acesso</label>
                  <input 
                    type="email" 
                    required 
                    placeholder="exemplo@mentorium.com" 
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    className="w-full p-3 rounded-lg border text-xs text-white bg-[#0a1520] outline-none transition-all focus:border-amber-400"
                    style={{ borderColor: COLORS.line }}
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono tracking-wider text-slate-400 uppercase mb-1">Senha</label>
                  <input 
                    type="password" 
                    required 
                    placeholder="Mínimo de 8 caracteres" 
                    value={registerPass}
                    onChange={(e) => setRegisterPass(e.target.value)}
                    className="w-full p-3 rounded-lg border text-xs text-white bg-[#0a1520] outline-none transition-all focus:border-amber-400"
                    style={{ borderColor: COLORS.line }}
                  />
                </div>

                <button 
                  type="submit" 
                  className="w-full py-3 rounded-lg text-xs font-bold transition-all mt-2" 
                  style={{ backgroundColor: COLORS.gold, color: COLORS.s3 }}
                >
                  Criar Minha Conta Gratuita
                </button>
              </form>
            )}

            <p className="text-center text-[10px] text-slate-500 mt-6">
              Ao continuar, concorda com os termos de uso e política de privacidade do ecossistema Mentorium.
            </p>
          </div>
        </div>
      )}

    </div>
  );
}