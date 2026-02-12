import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronDown, ChevronUp, MessageCircle, Mail, Phone } from 'lucide-react'
import styles from './HelpCenterPage.module.css'

interface FaqItem {
  question: string
  answer: string
}

const faqs: FaqItem[] = [
  {
    question: "Eslatmani qanday yarataman?",
    answer: "Asosiy sahifadagi qizil \"Yozib olish\" tugmasini bosing va eslatma haqida gapirib bering. Masalan: \"Ertaga soat 9 da uchrashuv\" yoki \"10 daqiqadan keyin dorixonaga bor\". Ilova avtomatik tushunadi va eslatma yaratadi."
  },
  {
    question: "Eslatma vaqtida jiringlamadi, nima qilishim kerak?",
    answer: "1. Telefon sozlamalarida \"Bezovta qilmaslik\" rejimi o'chirilganligini tekshiring.\n2. Profil → Alarm ovozini sozlash bo'limida ovoz yoqilganligini tekshiring.\n3. Ilova uchun \"Aniq vaqtda alarm\" ruxsati berilganligini tekshiring."
  },
  {
    question: "Eslatmani qanday o'zgartiraman?",
    answer: "Hozircha eslatmani o'zgartirish imkoniyati mavjud emas. Eslatmani o'chirish va yangisini yaratish orqali o'zgartirishingiz mumkin."
  },
  {
    question: "Takrorlanuvchi eslatma qanday ishlaydi?",
    answer: "\"Har kuni soat 8 da sport\" yoki \"Har dushanba uchrashuv\" kabi gapirsangiz, ilova avtomatik takrorlanuvchi eslatma yaratadi."
  },
  {
    question: "Ilovani bepul ishlatish mumkinmi?",
    answer: "Ha! Levi ilovasi to'liq bepul. Hech qanday yashirin to'lovlar yo'q."
  },
  {
    question: "Ma'lumotlarim xavfsizmi?",
    answer: "Ha, barcha ma'lumotlaringiz shifrlangan holda saqlanadi va uchinchi tomonlarga berilmaydi."
  }
]

export default function HelpCenterPage() {
  const navigate = useNavigate()
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const toggleFaq = (index: number) => {
    setOpenIndex(openIndex === index ? null : index)
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Yordam markazi</h1>
      </header>

      <div className={styles.content}>
        {/* FAQ Section */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>KO'P BERILADIGAN SAVOLLAR</h3>
          
          <div className={styles.faqList}>
            {faqs.map((faq, index) => (
              <div key={index} className={styles.faqItem}>
                <button 
                  className={styles.faqQuestion}
                  onClick={() => toggleFaq(index)}
                >
                  <span>{faq.question}</span>
                  {openIndex === index ? (
                    <ChevronUp size={20} />
                  ) : (
                    <ChevronDown size={20} />
                  )}
                </button>
                {openIndex === index && (
                  <div className={styles.faqAnswer}>
                    {faq.answer.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Contact Section */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>BOG'LANISH</h3>
          
          <div className={styles.contactCard}>
            <a href="https://t.me/levi_support" className={styles.contactItem}>
              <div className={styles.contactIcon}>
                <MessageCircle size={20} />
              </div>
              <div className={styles.contactInfo}>
                <span className={styles.contactLabel}>Telegram</span>
                <span className={styles.contactValue}>@levi_support</span>
              </div>
            </a>

            <div className={styles.divider} />

            <a href="mailto:support@levi.uz" className={styles.contactItem}>
              <div className={styles.contactIcon}>
                <Mail size={20} />
              </div>
              <div className={styles.contactInfo}>
                <span className={styles.contactLabel}>Email</span>
                <span className={styles.contactValue}>support@levi.uz</span>
              </div>
            </a>

            <div className={styles.divider} />

            <a href="tel:+998901234567" className={styles.contactItem}>
              <div className={styles.contactIcon}>
                <Phone size={20} />
              </div>
              <div className={styles.contactInfo}>
                <span className={styles.contactLabel}>Telefon</span>
                <span className={styles.contactValue}>+998 90 123 45 67</span>
              </div>
            </a>
          </div>
        </div>

        <p className={styles.footer}>
          Savollaringiz bo'lsa, biz bilan bog'laning. 24/7 yordam beramiz! 🙌
        </p>
      </div>
    </div>
  )
}
