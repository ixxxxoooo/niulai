import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import UiButton from './components/ui/UiButton.vue'
import UiInput from './components/ui/UiInput.vue'
import UiSelect from './components/ui/UiSelect.vue'
import UiCheckbox from './components/ui/UiCheckbox.vue'
import UiRadio from './components/ui/UiRadio.vue'
import UiTextarea from './components/ui/UiTextarea.vue'
import UiIcon from './components/ui/UiIcon.vue'

const app = createApp(App)
app.component('UiButton', UiButton)
app.component('UiInput', UiInput)
app.component('UiSelect', UiSelect)
app.component('UiCheckbox', UiCheckbox)
app.component('UiRadio', UiRadio)
app.component('UiTextarea', UiTextarea)
app.component('UiIcon', UiIcon)
app.mount('#app')
