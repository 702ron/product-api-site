import { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ShoppingCart, 
  Package, 
  TrendingUp, 
  BarChart3,
  CheckCircle,
  Star,
  ArrowRight,
  Play,
  Menu,
  X,
  Copy,
  Check
} from 'lucide-react';

const Homepage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navigation />
      <HeroSection />
      <FeaturesSection />
      <SocialProofSection />
      <InteractiveDemoSection />
      <PricingPreviewSection />
      <TrustSignalsSection />
      <CTASection />
      <Footer />
    </div>
  );
};

const Navigation = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Analytics tracking function
  const trackEvent = (eventName: string, properties?: Record<string, unknown>) => {
    // Analytics implementation would go here
    console.log('Track event:', eventName, properties);
  };

  const handleCTAClick = (source: string) => {
    trackEvent('cta_clicked', { source, page: 'homepage' });
  };

  return (
    <header className="relative bg-white border-b border-gray-200" role="banner">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-amazon-orange">Amazon Intelligence</h1>
          </div>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8" role="navigation" aria-label="Main navigation">
            <a 
              href="#features" 
              className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded"
              aria-label="Navigate to Features section"
            >
              Features
            </a>
            <a 
              href="#demo" 
              className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded"
              aria-label="Navigate to Demo section"
            >
              Demo
            </a>
            <a 
              href="#pricing" 
              className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded"
              aria-label="Navigate to Pricing section"
            >
              Pricing
            </a>
            <Link 
              to="/login" 
              className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded"
              aria-label="Sign in to your account"
            >
              Sign In
            </Link>
          </nav>

          <div className="hidden md:flex items-center space-x-4">
            <Link
              to="/register"
              onClick={() => handleCTAClick('header')}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-amazon-navy bg-amazon-orange hover:bg-amazon-orange-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amazon-orange transition-colors"
              aria-label="Start your free trial"
            >
              Start Free Trial
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded"
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={mobileMenuOpen ? 'Close mobile menu' : 'Open mobile menu'}
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div 
            id="mobile-menu" 
            className="md:hidden border-t border-gray-200 py-4"
            role="menu"
            aria-label="Mobile navigation menu"
          >
            <div className="flex flex-col space-y-4">
              <a 
                href="#features" 
                className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded px-2 py-1"
                role="menuitem"
                aria-label="Navigate to Features section"
                onClick={() => setMobileMenuOpen(false)}
              >
                Features
              </a>
              <a 
                href="#demo" 
                className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded px-2 py-1"
                role="menuitem"
                aria-label="Navigate to Demo section"
                onClick={() => setMobileMenuOpen(false)}
              >
                Demo
              </a>
              <a 
                href="#pricing" 
                className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded px-2 py-1"
                role="menuitem"
                aria-label="Navigate to Pricing section"
                onClick={() => setMobileMenuOpen(false)}
              >
                Pricing
              </a>
              <Link 
                to="/login" 
                className="text-gray-600 hover:text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded px-2 py-1"
                role="menuitem"
                aria-label="Sign in to your account"
                onClick={() => setMobileMenuOpen(false)}
              >
                Sign In
              </Link>
              <Link
                to="/register"
                onClick={() => {
                  handleCTAClick('mobile-menu');
                  setMobileMenuOpen(false);
                }}
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-amazon-navy bg-amazon-orange hover:bg-amazon-orange-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amazon-orange transition-colors"
                role="menuitem"
                aria-label="Start your free trial"
              >
                Start Free Trial
              </Link>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

const HeroSection = () => {
  // Analytics tracking function
  const trackEvent = (eventName: string, properties?: Record<string, unknown>) => {
    console.log('Track event:', eventName, properties);
  };

  const handleCTAClick = (source: string) => {
    trackEvent('cta_clicked', { source, page: 'homepage', section: 'hero' });
  };

  const handleDemoClick = () => {
    trackEvent('demo_clicked', { source: 'hero', page: 'homepage' });
    // Scroll to demo section
    document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative bg-gradient-to-r from-amazon-navy to-amazon-blue overflow-hidden" role="main">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-4xl md:text-6xl font-extrabold text-white leading-tight">
              Supercharge Your Amazon Business with{' '}
              <span className="text-amazon-orange">AI-Powered</span> Product Intelligence
            </h1>
            <p className="mt-6 text-xl text-blue-100 leading-relaxed">
              Access real-time Amazon data through our lightning-fast REST API. 
              Get product details, pricing, availability, and insights that power your success.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <Link
                to="/register"
                onClick={() => handleCTAClick('hero-primary')}
                className="inline-flex items-center justify-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-amazon-navy bg-amazon-orange hover:bg-amazon-orange-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amazon-orange transition-colors shadow-lg"
                aria-label="Start your free trial - no credit card required"
              >
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
              </Link>
              <button 
                onClick={handleDemoClick}
                className="inline-flex items-center justify-center px-8 py-4 border border-white text-lg font-medium rounded-lg text-white hover:bg-white hover:text-amazon-navy focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white transition-colors"
                aria-label="Watch product demo video"
              >
                <Play className="mr-2 h-5 w-5" aria-hidden="true" />
                Watch Demo
              </button>
            </div>
            <div className="mt-8 text-blue-100" role="list" aria-label="Trial benefits">
              <span className="text-sm">
                ✓ No credit card required  ✓ 1000 free API calls  ✓ Setup in 5 minutes
              </span>
            </div>
          </div>
        <div className="relative">
          {/* Interactive Code Demo Preview */}
          <div className="bg-gray-900 rounded-lg shadow-2xl overflow-hidden">
            <div className="px-6 py-4 bg-gray-800 border-b border-gray-700">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="ml-4 text-gray-400 text-sm">amazon-api-demo.js</span>
              </div>
            </div>
            <div className="p-6 font-mono text-sm">
              <div className="text-green-400">// Get Amazon product data in seconds</div>
              <div className="text-blue-400 mt-2">const response = await fetch(</div>
              <div className="text-yellow-300 ml-4">'https://api.amazonintel.com/products/B08N5WRWNW'</div>
              <div className="text-blue-400">);</div>
              <div className="text-purple-400 mt-2">console.log(response.title);</div>
              <div className="text-gray-300 mt-1">// "Echo Dot (4th Gen) | Smart speaker..."</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
  );
};

const FeaturesSection = () => {
  const features = [
    {
      icon: ShoppingCart,
      title: "Real-Time Product Data",
      description: "Access live Amazon product information including pricing, availability, ratings, and detailed specifications through our REST API.",
      stats: "10M+ products indexed"
    },
    {
      icon: Package,
      title: "FNSKU Conversion",
      description: "Convert ASINs to FNSKUs and vice versa with 99.9% accuracy. Bulk processing capabilities for enterprise needs.",
      stats: "99.9% accuracy rate"
    },
    {
      icon: TrendingUp,
      title: "Price Monitoring",
      description: "Set up automated price tracking with custom alerts. Get notified when prices drop or competitors change pricing.",
      stats: "Real-time alerts"
    },
    {
      icon: BarChart3,
      title: "Analytics & Insights",
      description: "Comprehensive analytics dashboard with usage metrics, trends, and actionable insights to optimize your business.",
      stats: "Advanced reporting"
    }
  ];

  return (
    <section id="features" className="py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Everything You Need to Dominate Amazon
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Our comprehensive API platform provides all the tools and data you need 
            to make informed decisions and stay ahead of the competition.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-center w-12 h-12 bg-amazon-orange bg-opacity-10 rounded-lg mb-4">
                <feature.icon className="h-6 w-6 text-amazon-orange" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-gray-600 mb-4">{feature.description}</p>
              <div className="text-sm font-medium text-amazon-blue">{feature.stats}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

const SocialProofSection = () => (
  <section className="py-16 bg-white">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-12">
        <h3 className="text-lg font-semibold text-gray-600 mb-8">
          Trusted by 1000+ Amazon Sellers Worldwide
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center opacity-70">
          {/* Customer logos placeholders */}
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-6 h-20 flex items-center justify-center border border-gray-200">
              <span className="text-gray-500 font-semibold">Company Logo</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Customer testimonials */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
        {[
          {
            quote: "Amazon Intelligence API has transformed our product research process. We can now analyze thousands of products in minutes instead of days.",
            author: "Sarah Johnson",
            role: "E-commerce Manager",
            company: "RetailTech Solutions"
          },
          {
            quote: "The FNSKU conversion tool saved us hundreds of hours. The accuracy is incredible and the API integration was seamless.",
            author: "Mike Chen",
            role: "Operations Director", 
            company: "Global Marketplace Co"
          },
          {
            quote: "Real-time price monitoring gives us a competitive edge. We can react to market changes instantly and optimize our pricing strategy.",
            author: "Lisa Rodriguez",
            role: "Business Owner",
            company: "EliteCommerce"
          }
        ].map((testimonial, index) => (
          <div key={index} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center mb-4">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-4 w-4 text-yellow-400 fill-current" />
              ))}
            </div>
            <p className="text-gray-600 mb-4">"{testimonial.quote}"</p>
            <div>
              <p className="font-semibold text-gray-900">{testimonial.author}</p>
              <p className="text-sm text-gray-500">{testimonial.role}, {testimonial.company}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

const InteractiveDemoSection = () => (
  <section id="demo" className="py-24 bg-white">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div>
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
            Try Our API Right Now
          </h2>
          <p className="text-xl text-gray-600 mb-8">
            No sign-up required. Test our Amazon Product Intelligence API 
            with real data and see the results instantly.
          </p>
          <div className="space-y-4">
            <div className="flex items-center">
              <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
              <span className="text-gray-700">Real Amazon product data</span>
            </div>
            <div className="flex items-center">
              <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
              <span className="text-gray-700">Live API responses</span>
            </div>
            <div className="flex items-center">
              <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
              <span className="text-gray-700">Multiple programming languages</span>
            </div>
          </div>
        </div>
        <div>
          <ApiDemoWidget />
        </div>
      </div>
    </div>
  </section>
);

const ApiDemoWidget = () => {
  const [selectedLanguage, setSelectedLanguage] = useState<'javascript' | 'python' | 'curl'>('javascript');
  const [copied, setCopied] = useState(false);

  const codeExamples: Record<'javascript' | 'python' | 'curl', string> = {
    javascript: `// JavaScript/Node.js
const response = await fetch(
  'https://api.amazonintel.com/products/B08N5WRWNW',
  {
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY',
      'Content-Type': 'application/json'
    }
  }
);

const product = await response.json();
console.log(product.title);
// "Echo Dot (4th Gen) | Smart speaker with Alexa"`,

    python: `# Python
import requests

response = requests.get(
    'https://api.amazonintel.com/products/B08N5WRWNW',
    headers={
        'Authorization': 'Bearer YOUR_API_KEY',
        'Content-Type': 'application/json'
    }
)

product = response.json()
print(product['title'])
# "Echo Dot (4th Gen) | Smart speaker with Alexa"`,

    curl: `# cURL
curl -X GET \\
  'https://api.amazonintel.com/products/B08N5WRWNW' \\
  -H 'Authorization: Bearer YOUR_API_KEY' \\
  -H 'Content-Type: application/json'

# Response:
# {
#   "title": "Echo Dot (4th Gen) | Smart speaker with Alexa",
#   "price": "$49.99",
#   "availability": "In Stock"
# }`
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(codeExamples[selectedLanguage]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-2xl overflow-hidden">
      <div className="px-6 py-4 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="ml-4 text-gray-400 text-sm">API Demo</span>
        </div>
        
        <div className="flex items-center space-x-2">
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value as 'javascript' | 'python' | 'curl')}
            className="bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600"
          >
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="curl">cURL</option>
          </select>
          
          <button
            onClick={handleCopy}
            className="text-gray-400 hover:text-white transition-colors"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
      </div>
      
      <div className="p-6 font-mono text-sm overflow-x-auto">
        <pre className="text-gray-300 whitespace-pre-wrap">
          {codeExamples[selectedLanguage]}
        </pre>
      </div>
    </div>
  );
};

const PricingPreviewSection = () => (
  <section id="pricing" className="py-24 bg-gray-50">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-16">
        <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
          Simple, Transparent Pricing
        </h2>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Pay only for what you use. Start free and scale as your business grows.
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          {
            name: "Starter",
            price: "Free",
            period: "",
            description: "Perfect for trying out our API",
            features: [
              "1,000 API calls/month",
              "Basic product data",
              "Email support",
              "Standard rate limits"
            ],
            cta: "Start Free Trial",
            highlight: false
          },
          {
            name: "Professional",
            price: "$99",
            period: "/month",
            description: "Best for growing businesses",
            features: [
              "50,000 API calls/month",
              "Advanced product data",
              "FNSKU conversion",
              "Priority support",
              "Webhooks & alerts"
            ],
            cta: "Start Free Trial",
            highlight: true
          },
          {
            name: "Enterprise",
            price: "Custom",
            period: "",
            description: "For high-volume operations",
            features: [
              "Unlimited API calls",
              "Custom data fields",
              "Dedicated support",
              "SLA guarantees",
              "Custom integrations"
            ],
            cta: "Contact Sales",
            highlight: false
          }
        ].map((plan, index) => (
          <div key={index} className={`bg-white rounded-lg shadow-sm border-2 p-8 ${plan.highlight ? 'border-amazon-orange' : 'border-gray-200'} relative`}>
            {plan.highlight && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-amazon-orange text-amazon-navy px-4 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </span>
              </div>
            )}
            
            <div className="text-center">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{plan.name}</h3>
              <div className="mb-4">
                <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                <span className="text-gray-600">{plan.period}</span>
              </div>
              <p className="text-gray-600 mb-6">{plan.description}</p>
              
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center">
                    <CheckCircle className="h-4 w-4 text-green-500 mr-3" />
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <Link
                to="/register"
                className={`w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md transition-colors ${
                  plan.highlight
                    ? 'text-amazon-navy bg-amazon-orange hover:bg-amazon-orange-dark'
                    : 'text-amazon-orange bg-amazon-orange bg-opacity-10 hover:bg-amazon-orange hover:bg-opacity-20'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          </div>
        ))}
      </div>
      
      <div className="text-center mt-12">
        <p className="text-gray-600 mb-4">
          Need more API calls? Volume discounts available for high-usage accounts.
        </p>
        <Link to="/pricing" className="text-amazon-blue hover:text-amazon-blue-dark font-medium">
          View detailed pricing →
        </Link>
      </div>
    </div>
  </section>
);

const TrustSignalsSection = () => (
  <section className="py-16 bg-white">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
        <div>
          <div className="text-3xl font-bold text-amazon-orange mb-2">99.9%</div>
          <div className="text-gray-600">API Uptime SLA</div>
          <p className="text-sm text-gray-500 mt-2">Guaranteed reliability for your business</p>
        </div>
        <div>
          <div className="text-3xl font-bold text-amazon-orange mb-2">10M+</div>
          <div className="text-gray-600">API Calls Monthly</div>
          <p className="text-sm text-gray-500 mt-2">Trusted by thousands of developers</p>
        </div>
        <div>
          <div className="text-3xl font-bold text-amazon-orange mb-2">&lt;200ms</div>
          <div className="text-gray-600">Average Response Time</div>
          <p className="text-sm text-gray-500 mt-2">Lightning-fast API responses</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
        <div className="text-center">
          <div className="bg-amazon-orange bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-8 w-8 text-amazon-orange" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">SOC 2 Compliant</h3>
          <p className="text-gray-600">Enterprise-grade security and compliance standards</p>
        </div>
        <div className="text-center">
          <div className="bg-amazon-blue bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <ShoppingCart className="h-8 w-8 text-amazon-blue" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Amazon Official Data</h3>
          <p className="text-gray-600">Real-time data directly from Amazon's marketplace</p>
        </div>
        <div className="text-center">
          <div className="bg-amazon-navy bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="h-8 w-8 text-amazon-navy" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">24/7 Monitoring</h3>
          <p className="text-gray-600">Continuous monitoring and proactive support</p>
        </div>
      </div>
    </div>
  </section>
);

const CTASection = () => (
  <section className="py-24 bg-amazon-navy">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
        Ready to Supercharge Your Amazon Business?
      </h2>
      <p className="text-xl text-blue-100 mb-8 max-w-3xl mx-auto">
        Join thousands of successful Amazon sellers who use our API to gain competitive advantages 
        and grow their businesses faster.
      </p>
      
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Link
          to="/register"
          className="inline-flex items-center justify-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-amazon-navy bg-amazon-orange hover:bg-amazon-orange-dark transition-colors shadow-lg"
        >
          Start Free Trial
          <ArrowRight className="ml-2 h-5 w-5" />
        </Link>
        <button className="inline-flex items-center justify-center px-8 py-4 border border-white text-lg font-medium rounded-lg text-white hover:bg-white hover:text-amazon-navy transition-colors">
          <Play className="mr-2 h-5 w-5" />
          Schedule Demo
        </button>
      </div>
      
      <p className="text-blue-200 text-sm mt-6">
        No credit card required • 1000 free API calls • Setup in 5 minutes
      </p>
    </div>
  </section>
);

const Footer = () => (
  <footer className="bg-gray-900">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="col-span-1 md:col-span-2">
          <h3 className="text-2xl font-bold text-white mb-4">Amazon Intelligence</h3>
          <p className="text-gray-300 mb-6 max-w-md">
            The most comprehensive Amazon Product Intelligence API platform. 
            Get real-time data, insights, and tools to dominate the marketplace.
          </p>
          <div className="flex space-x-4">
            <Link to="/register" className="bg-amazon-orange text-amazon-navy px-6 py-2 rounded-md hover:bg-amazon-orange-dark transition-colors">
              Start Free Trial
            </Link>
          </div>
        </div>
        
        <div>
          <h4 className="text-white font-semibold mb-4">Product</h4>
          <ul className="space-y-2">
            <li><a href="#features" className="text-gray-300 hover:text-white transition-colors">Features</a></li>
            <li><a href="#pricing" className="text-gray-300 hover:text-white transition-colors">Pricing</a></li>
            <li><a href="#demo" className="text-gray-300 hover:text-white transition-colors">Demo</a></li>
            <li><Link to="/docs" className="text-gray-300 hover:text-white transition-colors">Documentation</Link></li>
          </ul>
        </div>
        
        <div>
          <h4 className="text-white font-semibold mb-4">Company</h4>
          <ul className="space-y-2">
            <li><Link to="/about" className="text-gray-300 hover:text-white transition-colors">About</Link></li>
            <li><Link to="/contact" className="text-gray-300 hover:text-white transition-colors">Contact</Link></li>
            <li><Link to="/privacy" className="text-gray-300 hover:text-white transition-colors">Privacy</Link></li>
            <li><Link to="/terms" className="text-gray-300 hover:text-white transition-colors">Terms</Link></li>
          </ul>
        </div>
      </div>
      
      <div className="border-t border-gray-800 mt-12 pt-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <p className="text-gray-400 text-sm">
            © 2024 Amazon Intelligence. All rights reserved.
          </p>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <span className="text-gray-400 text-sm">SOC 2 Compliant</span>
            <span className="text-gray-400 text-sm">99.9% SLA</span>
            <span className="text-gray-400 text-sm">24/7 Support</span>
          </div>
        </div>
      </div>
    </div>
  </footer>
);

export default Homepage;