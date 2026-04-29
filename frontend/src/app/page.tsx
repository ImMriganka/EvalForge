export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">EvalForge</h1>
          <p className="mt-1 text-gray-500">
            LLM Agent Benchmarking &amp; Trustworthiness Platform
          </p>
        </div>

        {/* KPI Cards — placeholders for Phase 5 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Experiments",      value: "—", color: "bg-indigo-50 text-indigo-700"  },
            { label: "Avg Faithfulness", value: "—", color: "bg-green-50  text-green-700"   },
            { label: "Avg Trust Score",  value: "—", color: "bg-blue-50   text-blue-700"    },
            { label: "Injection Rate",   value: "—", color: "bg-red-50    text-red-700"     },
          ].map((card) => (
            <div key={card.label} className={`rounded-xl p-5 shadow-sm ${card.color}`}>
              <p className="text-xs uppercase tracking-wide opacity-70">{card.label}</p>
              <p className="text-3xl font-bold mt-1">{card.value}</p>
            </div>
          ))}
        </div>

        {/* Navigation */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { href: "/experiments", title: "Experiments",   desc: "Browse and compare evaluation runs"      },
            { href: "/datasets",    title: "Datasets",      desc: "Upload and manage test datasets"         },
            { href: "/injection",   title: "Injection Tests", desc: "Run prompt injection attack suite"    },
          ].map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="block rounded-xl border bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              <h2 className="font-semibold text-gray-800">{link.title}</h2>
              <p className="mt-1 text-sm text-gray-500">{link.desc}</p>
            </a>
          ))}
        </div>

        <p className="mt-10 text-xs text-gray-400 text-center">
          Phase 1 scaffold — API at{" "}
          <code className="bg-gray-100 px-1 rounded">http://localhost:8000</code>
        </p>
      </div>
    </main>
  );
}
