import { useState, useRef, useCallback, useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { ApiError } from '@/api/client'
import * as authApi from '@/api/auth'
import { showToast } from '@/components/shared/Toast'
import { cn } from '@/utils/cn'

/* 震动动画 keyframes（内联注入） */
const shakeKeyframes = `
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
  20%, 40%, 60%, 80% { transform: translateX(4px); }
}
`

/* ---- 验证工具 ---- */
const USERNAME_RE = /^[a-zA-Z0-9_]{4,20}$/
const HAS_UPPER = /[A-Z]/
const HAS_LOWER = /[a-z]/
const HAS_DIGIT = /\d/
const HAS_SPECIAL = /[^a-zA-Z0-9]/

function validateUsername(v: string): string {
  if (!v.trim()) return '请输入用户名'
  if (v.length < 4 || v.length > 20) return '用户名需为4-20个字符'
  if (!USERNAME_RE.test(v)) return '用户名仅支持字母、数字和下划线'
  return ''
}

function validateEmail(v: string): string {
  if (!v.trim()) return '请输入邮箱'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return '请输入有效的邮箱地址'
  return ''
}

function validatePassword(v: string, isLogin: boolean): string {
  if (!v) return '请输入密码'
  if (isLogin) return '' // 登录模式不校验复杂度
  if (v.length < 8) return '密码至少8个字符'
  if (!HAS_UPPER.test(v) || !HAS_LOWER.test(v) || !HAS_DIGIT.test(v) || !HAS_SPECIAL.test(v))
    return '密码需包含大写字母、小写字母、数字和特殊字符'
  return ''
}

interface PasswordCheck {
  label: string
  pass: boolean
}

function getPasswordChecks(v: string): PasswordCheck[] {
  return [
    { label: '至少8个字符', pass: v.length >= 8 },
    { label: '包含大写字母', pass: HAS_UPPER.test(v) },
    { label: '包含小写字母', pass: HAS_LOWER.test(v) },
    { label: '包含数字', pass: HAS_DIGIT.test(v) },
    { label: '包含特殊字符', pass: HAS_SPECIAL.test(v) },
  ]
}

/* ---- 内联提示条 ---- */
interface AlertBannerProps {
  type: 'error' | 'success'
  message: string
  onClose: () => void
}

function AlertBanner({ type, message, onClose }: AlertBannerProps) {
  useEffect(() => {
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [onClose])

  const colors =
    type === 'error'
      ? 'bg-red-50 border-red-300 text-red-700'
      : 'bg-green-50 border-green-300 text-green-700'

  return (
    <div className={`mb-4 flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${colors} animate-[fadeIn_0.25s_ease]`}>
      <span className="flex-1">{message}</span>
      <button onClick={onClose} className="ml-2 opacity-60 hover:opacity-100 transition-opacity">✕</button>
    </div>
  )
}

/* ---- 主组件 ---- */
export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // 是否已交互过（touched），用于决定是否实时显示错误
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  // 页面级提示
  const [alert, setAlert] = useState<{ type: 'error' | 'success'; message: string } | null>(null)

  // 动画状态
  const [pageExiting, setPageExiting] = useState(false)
  const [formTransition, setFormTransition] = useState<'idle' | 'out' | 'in'>('idle')
  const [shaking, setShaking] = useState(false)

  const { login } = useAuthStore()
  const formRef = useRef<HTMLFormElement>(null)

  const triggerShake = () => {
    setShaking(true)
    setTimeout(() => setShaking(false), 500)
  }

  const dismissAlert = useCallback(() => setAlert(null), [])

  /* ---- 实时验证 ---- */
  const liveErrors = useCallback((): Record<string, string> => {
    const e: Record<string, string> = {}
    const uErr = validateUsername(username)
    if (uErr) e.username = uErr
    if (!isLogin) {
      const eErr = validateEmail(email)
      if (eErr) e.email = eErr
    }
    const pErr = validatePassword(password, isLogin)
    if (pErr) e.password = pErr
    return e
  }, [username, email, password, isLogin])

  /* 提交时的完整校验 */
  const validate = (): boolean => {
    const newErrors = liveErrors()
    setErrors(newErrors)
    // 将所有字段标记为 touched
    setTouched({ username: true, email: true, password: true })
    return Object.keys(newErrors).length === 0
  }

  const handleFieldChange = (field: string, value: string, setter: (v: string) => void) => {
    setter(value)
    setTouched((prev) => ({ ...prev, [field]: true }))
    // 清除之前的提交错误
    setErrors((prev) => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  /* 获取某字段的显示错误（仅 touched 后才显示） */
  const fieldError = (field: string): string | undefined => {
    if (!touched[field]) return undefined
    // 提交产生的错误优先
    if (errors[field]) return errors[field]
    // 否则用实时计算
    const live = liveErrors()
    return live[field]
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setAlert(null)
    if (!validate()) {
      triggerShake()
      return
    }
    setLoading(true)

    try {
      if (isLogin) {
        await login(username, password)
        showToast('success', '登录成功！欢迎回来', 2000)
        setPageExiting(true)
        await new Promise((r) => setTimeout(r, 500))
      } else {
        await authApi.register(username, email, password)
        setAlert({ type: 'success', message: '注册成功！即将跳转到登录...' })

        const savedUsername = username

        setFormTransition('out')
        await new Promise((r) => setTimeout(r, 400))

        setIsLogin(true)
        setUsername(savedUsername)
        setEmail('')
        setPassword('')
        setTouched({})
        setErrors({})

        setFormTransition('in')
        await new Promise((r) => setTimeout(r, 50))
        setFormTransition('idle')
      }
    } catch (err) {
      setPageExiting(false)
      const msg = err instanceof ApiError ? err.message : '连接失败，请检查网络后重试'
      setAlert({ type: 'error', message: msg })
      triggerShake()
    } finally {
      setLoading(false)
    }
  }

  const switchTab = (toLogin: boolean) => {
    if (toLogin === isLogin) return
    setErrors({})
    setTouched({})
    setAlert(null)
    setFormTransition('out')
    setTimeout(() => {
      setIsLogin(toLogin)
      setPassword('')
      if (toLogin) setEmail('')
      setFormTransition('in')
      setTimeout(() => setFormTransition('idle'), 50)
    }, 250)
  }

  const formAnimClass =
    formTransition === 'out'
      ? 'opacity-0 translate-y-2'
      : formTransition === 'in'
        ? 'opacity-0 -translate-y-2'
        : 'opacity-100 translate-y-0'

  const inputCls = (field: string) =>
    cn(
      'w-full rounded-xl bg-plum-50/50 px-4 py-2.5 text-sm text-ink outline-none transition-colors border focus:ring-2',
      fieldError(field)
        ? 'border-red-400 focus:border-red-500 focus:ring-red-200'
        : touched[field] && !fieldError(field) && (field === 'username' ? username : field === 'email' ? email : password)
          ? 'border-green-400 focus:border-green-500 focus:ring-green-200'
          : 'border-plum-200 focus:border-plum-400 focus:ring-plum-200',
    )

  const pwChecks = getPasswordChecks(password)

  return (
    <>
      <style>{shakeKeyframes}{`@keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}`}</style>
      <div
        className={`flex min-h-screen items-center justify-center bg-gradient-to-br from-plum-50 via-white to-plum-100 transition-opacity duration-500 ${
          pageExiting ? 'opacity-0' : 'opacity-100'
        }`}
      >
        <div className="w-full max-w-sm px-4">
          {/* Logo */}
          <div className="mb-8 text-center">
            <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-plum-400 to-plum-600 text-2xl font-bold text-white shadow-lg shadow-plum-300/40">
              玄
            </div>
            <h1 className="text-2xl font-bold text-ink">璇玑</h1>
            <p className="mt-1 text-sm text-ink-light">AI 智能体系统</p>
          </div>

          {/* 卡片 */}
          <div className="rounded-2xl border border-plum-100 bg-white p-6 shadow-xl shadow-plum-200/20">
            {/* 选项卡 */}
            <div className="mb-5 flex rounded-lg bg-plum-50 p-1">
              <button
                onClick={() => switchTab(true)}
                className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                  isLogin ? 'bg-white text-ink shadow-sm' : 'text-ink-light'
                }`}
              >
                登录
              </button>
              <button
                onClick={() => switchTab(false)}
                className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                  !isLogin ? 'bg-white text-ink shadow-sm' : 'text-ink-light'
                }`}
              >
                注册
              </button>
            </div>

            {/* 提示框 */}
            {alert && <AlertBanner type={alert.type} message={alert.message} onClose={dismissAlert} />}

            {/* 表单 */}
            <form
              ref={formRef}
              onSubmit={handleSubmit}
              noValidate
              className={`space-y-4 transition-all duration-300 ${formAnimClass}`}
              style={shaking ? { animation: 'shake 0.4s ease-in-out' } : undefined}
            >
              {/* 用户名 */}
              <div>
                <input
                  type="text"
                  placeholder="请输入用户名"
                  value={username}
                  onChange={(e) => handleFieldChange('username', e.target.value, setUsername)}
                  onBlur={() => setTouched((p) => ({ ...p, username: true }))}
                  className={inputCls('username')}
                />
                {fieldError('username') && (
                  <p className="mt-1 text-xs text-red-500">{fieldError('username')}</p>
                )}
                {!isLogin && touched.username && !fieldError('username') && username && (
                  <p className="mt-1 text-xs text-green-600">用户名格式正确</p>
                )}
              </div>

              {/* 邮箱（仅注册） */}
              {!isLogin && (
                <div>
                  <input
                    type="email"
                    placeholder="请输入邮箱"
                    value={email}
                    onChange={(e) => handleFieldChange('email', e.target.value, setEmail)}
                    onBlur={() => setTouched((p) => ({ ...p, email: true }))}
                    className={inputCls('email')}
                  />
                  {fieldError('email') && (
                    <p className="mt-1 text-xs text-red-500">{fieldError('email')}</p>
                  )}
                </div>
              )}

              {/* 密码 */}
              <div>
                <input
                  type="password"
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => handleFieldChange('password', e.target.value, setPassword)}
                  onBlur={() => setTouched((p) => ({ ...p, password: true }))}
                  className={inputCls('password')}
                />
                {fieldError('password') && isLogin && (
                  <p className="mt-1 text-xs text-red-500">{fieldError('password')}</p>
                )}

                {/* 注册模式：密码复杂度清单 */}
                {!isLogin && (touched.password || password.length > 0) && (
                  <ul className="mt-2 space-y-1">
                    {pwChecks.map((c) => (
                      <li key={c.label} className={`flex items-center gap-1.5 text-xs ${c.pass ? 'text-green-600' : 'text-ink-lighter'}`}>
                        <span className={c.pass ? 'text-green-500' : 'text-red-400'}>{c.pass ? '✓' : '✗'}</span>
                        {c.label}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 提交按钮 */}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-gradient-to-r from-plum-500 to-plum-600 py-2.5 text-sm font-medium text-white shadow-md shadow-plum-300/30 transition-all hover:shadow-lg disabled:opacity-60"
              >
                {loading ? '处理中...' : isLogin ? '登录' : '注册'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  )
}
