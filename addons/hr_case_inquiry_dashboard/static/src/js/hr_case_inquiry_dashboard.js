/** @odoo-module **/

(function() {
    'use strict';

    const InquiryDashboard = {
        state: {
            employeeName: "",
            email: "",
            phone: "",
            inquiryTypes: [],
            categoryId: "",
            description: "",
            errors: {},
            submitting: false,
            submitError: "",
            caseName: "",
        },

        init() {
            const root = document.getElementById("hr_case_inquiry_dashboard_root");
            if (!root) return;

            this.state.employeeName = root.dataset.employeeName || "User";
            this.render();
            this.attachEventListeners();
            this.loadOptions();
        },

        render() {
            const formContainer = document.getElementById("hcid-form-container");
            if (!formContainer) return;

            formContainer.innerHTML = `
                <div class="hcid-body">
                    <div class="hcid-form-header">
                        <h2 class="hcid-title">Employee Services Inquiry</h2>
                        <p class="hcid-subtitle">Choose the issue type that best matches your request. This helps route your inquiry to the right HR service.</p>
                    </div>
                    <p class="hcid-required-note">
                        <span class="hcid-required-star">*</span> Indicates required
                    </p>

                    <div class="hcid-grid">
                        <div class="hcid-field">
                            <label class="hcid-label">
                                <span class="hcid-required-star">*</span> Inquiry Raised By
                            </label>
                            <div class="hcid-input-disabled">
                                <i class="fa fa-info-circle hcid-info-icon"></i>
                                <span>${this.escapeHtml(this.state.employeeName)}</span>
                            </div>
                        </div>

                        <div class="hcid-field">
                            <label class="hcid-label">Badge Number</label>
                            <div class="hcid-input-disabled hcid-input-empty"></div>
                        </div>

                        <div class="hcid-field">
                            <label class="hcid-label">Email Address</label>
                            <div class="hcid-input-disabled">
                                <i class="fa fa-info-circle hcid-info-icon"></i>
                                <span>${this.escapeHtml(this.state.email)}</span>
                            </div>
                        </div>

                        <div class="hcid-field">
                            <label class="hcid-label">Phone Number</label>
                            <div class="hcid-input-disabled">
                                <span>${this.escapeHtml(this.state.phone)}</span>
                            </div>
                        </div>
                    </div>

                    <p class="hcid-helper-text">
                        <span class="hcid-required-star">*</span>
                        This is the phone number and email we will use to contact you. If the
                        information is incorrect, please update it in your profile to ensure
                        you receive all updates related to your request.
                    </p>

                    <div class="hcid-field hcid-field-full">
                        <label class="hcid-label">
                            <span class="hcid-required-star">*</span> Type of Inquiry
                        </label>
                        <select id="hcid-category-select" class="hcid-select ${this.state.errors.category_id ? 'hcid-input-error' : ''}">
                            <option value="">-- None --</option>
                            ${this.state.inquiryTypes.map(opt => `<option value="${opt.id}" ${String(this.state.categoryId) === String(opt.id) ? 'selected' : ''}>${this.escapeHtml(opt.service_name ? opt.service_name + ' — ' + opt.name : opt.name)}</option>`).join('')}
                        </select>
                        ${this.state.errors.category_id ? `<p class="hcid-error-text">${this.escapeHtml(this.state.errors.category_id)}</p>` : ''}
                    </div>

                    <div class="hcid-field hcid-field-full">
                        <label class="hcid-label">
                            <span class="hcid-required-star">*</span>
                            Please provide the details of your Inquiry in the box below.
                        </label>
                        <textarea id="hcid-description-input" class="hcid-textarea ${this.state.errors.description ? 'hcid-input-error' : ''}" rows="5">${this.escapeHtml(this.state.description)}</textarea>
                        ${this.state.errors.description ? `<p class="hcid-error-text">${this.escapeHtml(this.state.errors.description)}</p>` : ''}
                    </div>
                </div>

                <div class="hcid-attachments-section">
                    <p class="hcid-attachments-label">Add attachments</p>
                    <div class="hcid-dropzone">
                        <i class="fa fa-cloud-upload hcid-dropzone-icon"></i>
                        <p class="hcid-dropzone-text">
                            <span class="hcid-dropzone-link">Choose a file</span> or drag it here.
                        </p>
                        <p class="hcid-dropzone-subtext">Copy and paste clipboard files here.</p>
                    </div>
                </div>

                <div class="hcid-footer">
                    ${this.state.submitError ? `<p class="hcid-submit-error">${this.escapeHtml(this.state.submitError)}</p>` : ''}
                    <button id="hcid-submit-btn" class="hcid-submit-btn" type="button" ${this.state.submitting ? 'disabled' : ''}>
                        ${this.state.submitting ? '<i class="fa fa-circle-o-notch fa-spin"/> Submitting...' : 'Submit'}
                    </button>
                </div>
            `;

            this.attachEventListeners();
        },

        attachEventListeners() {
            const categorySelect = document.getElementById("hcid-category-select");
            if (categorySelect) {
                categorySelect.addEventListener("change", (e) => {
                    this.state.categoryId = e.target.value;
                    if (this.state.categoryId) {
                        delete this.state.errors.category_id;
                    }
                });
            }

            const descriptionInput = document.getElementById("hcid-description-input");
            if (descriptionInput) {
                descriptionInput.addEventListener("input", (e) => {
                    this.state.description = e.target.value;
                    if (this.state.description.trim()) {
                        delete this.state.errors.description;
                    }
                });
            }

            const submitBtn = document.getElementById("hcid-submit-btn");
            if (submitBtn) {
                submitBtn.addEventListener("click", () => this.onSubmit());
            }
        },

        escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            if (text === null || text === undefined) {
                return '';
            }
            return String(text).replace(/[&<>"']/g, m => map[m]);
        },

        async rpcCall(endpoint, data) {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                throw new Error(`RPC call failed: ${response.statusText}`);
            }
            return await response.json();
        },

        async loadOptions() {
            try {
                const data = await this.rpcCall("/employee-services/inquiry/options", {});
                this.state.employeeName = data.employee_name || this.state.employeeName;
                this.state.email = data.email || "";
                this.state.phone = data.phone || "";
                this.state.inquiryTypes = data.inquiry_types || [];
                this.render();
            } catch (error) {
                this.state.submitError = "We couldn't load the inquiry form. Please refresh the page.";
                console.error("Failed to load options:", error);
            }
        },

        validate() {
            const errors = {};
            if (!this.state.categoryId) {
                errors.category_id = "Please select a Type of Inquiry.";
            }
            if (!this.state.description || !this.state.description.trim()) {
                errors.description = "Please provide the details of your inquiry.";
            }
            this.state.errors = errors;
            return Object.keys(errors).length === 0;
        },

        async onSubmit() {
            this.state.submitError = "";
            if (!this.validate()) {
                this.render();
                return;
            }
            this.state.submitting = true;
            this.render();
            try {
                const result = await this.rpcCall("/employee-services/inquiry/submit", {
                    category_id: this.state.categoryId,
                    description: this.state.description,
                    source: "self_service",
                });
                this.state.caseName = (result.case && result.case.name) || "";
                this.showSuccessScreen();
            } catch (error) {
                const message =
                    (error && error.data && error.data.message) ||
                    "Something went wrong while submitting your inquiry. Please try again.";
                this.state.submitError = message;
                console.error("Failed to submit inquiry:", error);
            } finally {
                this.state.submitting = false;
                this.render();
            }
        },

        showSuccessScreen() {
            const formContainer = document.getElementById("hcid-form-container");
            const successContainer = document.getElementById("hcid-success-container");
            const caseNameSpan = document.getElementById("hcid-case-name");

            if (formContainer) formContainer.style.display = "none";
            if (successContainer) successContainer.style.display = "block";
            if (caseNameSpan) caseNameSpan.textContent = this.escapeHtml(this.state.caseName);
        },
    };

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        InquiryDashboard.init();
    });
})();
