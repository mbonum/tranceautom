/**
 * Modern Table View - JavaScript functionality
 * Handles inline editing, pagination, search for table layout
 */

class ModernTableView {
    constructor() {
        this.currentPage = 1;
        this.perPage = 25;
        this.searchQuery = '';
        this.filters = {};
        this.modifiedProducts = new Set();
        this.savingProducts = new Set();
        this.selectedProducts = new Set();
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupAutosave();
        this.loadInitialData();
    }
    
    bindEvents() {
        // Search functionality
        $('#search-input').on('input', this.debounce(this.handleSearch.bind(this), 300));
        $('#reset-search').on('click', this.resetSearch.bind(this));
        
        // Status filter checkboxes
        $('.status-filters input[type="checkbox"]').on('change', this.handleStatusFilter.bind(this));
        
        // Pagination
        $('#per-page-select').on('change', this.handlePerPageChange.bind(this));
        $(document).on('click', '.page-link', this.handlePageClick.bind(this));
        
        // Product selection
        $('#select-all-checkbox').on('change', this.handleSelectAll.bind(this));
        $(document).on('change', '.product-selector', this.handleProductSelection.bind(this));
        $('#select-all').on('click', this.selectAllVisible.bind(this));
        
        // Inline editing
        $(document).on('input change', '.editable', this.handleFieldChange.bind(this));
        $(document).on('blur', '.editable', this.handleFieldBlur.bind(this));
        $(document).on('keypress', '.editable', this.handleFieldKeypress.bind(this));
        
        // Save and undo actions
        $(document).on('click', '.save-btn', this.saveProduct.bind(this));
        $(document).on('click', '.undo-btn', this.undoProduct.bind(this));
        $('#save-all-btn').on('click', this.saveAllModified.bind(this));
        
        // Country modal
        $(document).on('click', '.countries-more', this.openCountryModal.bind(this));
        $('#save-countries').on('click', this.saveCountries.bind(this));
        
        // Bulk operations
        $('#apply-bulk-changes').on('click', this.applyBulkChanges.bind(this));
        $('#apply-visibility-rules').on('click', this.applyVisibilityRules.bind(this));
        $('#auto-apply-rule').on('click', this.applyVisibilityRules.bind(this));
    }
    
    setupAutosave() {
        // Auto-save modified products every 45 seconds
        setInterval(() => {
            if (this.modifiedProducts.size > 0) {
                this.saveAllModified();
            }
        }, 45000);
    }
    
    loadInitialData() {
        this.updatePaginationInfo();
        this.updateSelectionState();
    }
    
    // Search and Filter Methods
    handleSearch(event) {
        this.searchQuery = event.target.value;
        this.currentPage = 1;
        this.loadProducts();
    }
    
    resetSearch() {
        $('#search-input').val('');
        this.searchQuery = '';
        this.currentPage = 1;
        this.loadProducts();
    }
    
    handleStatusFilter(event) {
        const filterId = event.target.id;
        const isChecked = event.target.checked;
        
        if (isChecked) {
            this.filters[filterId] = true;
        } else {
            delete this.filters[filterId];
        }
        
        this.filterProductsLocally();
    }
    
    filterProductsLocally() {
        const rows = $('.product-row');
        
        rows.each((index, element) => {
            const $row = $(element);
            let show = true;
            
            // Check status filters
            if (this.filters['filter-modified'] && !$row.hasClass('modified')) {
                show = false;
            }
            
            if (this.filters['filter-no-countries'] && $row.find('.country-tag').length > 0) {
                show = false;
            }
            
            $row.toggle(show);
        });
        
        this.updateVisibleCount();
    }
    
    // Pagination Methods
    handlePerPageChange(event) {
        this.perPage = parseInt(event.target.value);
        this.currentPage = 1;
        this.loadProducts();
    }
    
    handlePageClick(event) {
        event.preventDefault();
        const page = $(event.currentTarget).data('page');
        if (page && page !== this.currentPage) {
            this.currentPage = page;
            this.loadProducts();
        }
    }
    
    loadProducts(append = false) {
        const $loadingIndicator = $('#loading-indicator');
        const $tbody = $('#products-tbody');
        const $noResults = $('#no-results');
        
        $loadingIndicator.show();
        $('#products-table').addClass('loading');
        
        // Prepare request data
        const requestData = {
            page: this.currentPage,
            per_page: this.perPage,
            search: this.searchQuery,
            ...this.filters
        };
        
        $.ajax({
            url: window.location.pathname,
            method: 'GET',
            data: requestData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: (response) => {
                $loadingIndicator.hide();
                $('#products-table').removeClass('loading');
                
                if (response.products && response.products.length > 0) {
                    if (append) {
                        $tbody.append(response.html);
                    } else {
                        $tbody.html(response.html);
                    }
                    
                    $noResults.hide();
                    this.updatePaginationInfo(response.pagination);
                } else {
                    if (!append) {
                        $tbody.empty();
                        $noResults.show();
                    }
                }
                
                this.updateSelectionState();
                this.updatePaginationNav(response.pagination);
            },
            error: (xhr, status, error) => {
                $loadingIndicator.hide();
                $('#products-table').removeClass('loading');
                this.showError('Failed to load products: ' + error);
            }
        });
    }
    
    updatePaginationInfo(pagination = null) {
        if (pagination) {
            if (pagination.total > 0) {
                $('#pagination-text').text(`Showing ${pagination.start}-${pagination.end} of ${pagination.total} products`);
            } else {
                $('#pagination-text').text('No products found');
            }
        }
    }

    updatePaginationNav(pagination) {
        const $nav = $('#pagination-nav');
        if (!$nav.length || !pagination) return;

        let html = '';

        if (pagination.has_previous) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1"><i class="bi bi-chevron-double-left"></i></a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.previous_page_number}"><i class="bi bi-chevron-left"></i></a></li>`;
        }

        // Simplified pagination links logic for demonstration
        const startPage = Math.max(1, pagination.current_page - 2);
        const endPage = Math.min(pagination.total_pages, pagination.current_page + 2);

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            if (i === pagination.current_page) {
                html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
            }
        }

        if (endPage < pagination.total_pages) {
            if (endPage < pagination.total_pages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.total_pages}">${pagination.total_pages}</a></li>`;
        }

        if (pagination.has_next) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.next_page_number}"><i class="bi bi-chevron-right"></i></a></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.total_pages}"><i class="bi bi-chevron-double-right"></i></a></li>`;
        }

        $nav.html(html); // This line was missing
    }
    
    updateVisibleCount() {
        const visibleCount = $('.product-row:visible').length;
        const totalCount = $('.product-row').length;
        $('#pagination-text').text(`Showing ${visibleCount} of ${totalCount} products (filtered)`);
    }
    
    // Selection Methods
    handleSelectAll(event) {
        const isChecked = event.target.checked;
        $('.product-selector:visible').prop('checked', isChecked);
        this.updateSelectedProducts();
    }
    
    selectAllVisible() {
        $('.product-selector:visible').prop('checked', true);
        this.updateSelectedProducts();
    }
    
    handleProductSelection(event) {
        this.updateSelectedProducts();
    }
    
    updateSelectedProducts() {
        this.selectedProducts.clear();
        $('.product-selector:checked').each((index, element) => {
            this.selectedProducts.add($(element).val());
        });
        
        this.updateSelectionState();
    }
    
    updateSelectionState() {
        const selectedCount = this.selectedProducts.size;
        const visibleCount = $('.product-selector:visible').length;
        const checkedCount = $('.product-selector:checked').length;
        
        // Update select all checkbox
        $('#select-all-checkbox').prop('indeterminate', checkedCount > 0 && checkedCount < visibleCount);
        $('#select-all-checkbox').prop('checked', checkedCount === visibleCount && visibleCount > 0);
        
        // Show/hide bulk operations
        if (selectedCount > 0) {
            this.showBulkOperationsButton();
            $('#selected-count').text(selectedCount);
        } else {
            this.hideBulkOperationsButton();
        }
    }
    
    // Editing Methods
    handleFieldChange(event) {
        const $field = $(event.currentTarget);
        const $row = $field.closest('.product-row');
        const productId = $row.data('product-id');
        const fieldName = $field.data('field');
        const originalValue = $field.data('original') || '';
        const currentValue = $field.val();
        
        // Mark field as modified if value changed
        if (currentValue !== originalValue) {
            $field.addClass('modified');
            $row.addClass('modified');
            this.modifiedProducts.add(productId);
            this.showRowActions($row);
        } else {
            $field.removeClass('modified');
            this.checkIfProductStillModified($row);
        }
        
        this.updateSaveButtonState();
    }
    
    handleFieldBlur(event) {
        // Optional: Could trigger auto-save on field blur
        const $field = $(event.currentTarget);
        if ($field.hasClass('modified')) {
            // Validate field if needed
            this.validateField($field);
        }
    }
    
    handleFieldKeypress(event) {
        if (event.which === 13) { // Enter key
            event.preventDefault();
            const $field = $(event.currentTarget);
            const $row = $field.closest('.product-row');
            
            if ($row.hasClass('modified')) {
                this.saveProduct(event);
            }
        }
    }
    
    validateField($field) {
        const fieldName = $field.data('field');
        const value = $field.val();
        
        // Basic validation
        $field.removeClass('error');
        
        // Check required fields
        if (['chiave_articolo', 'sku'].includes(fieldName) && !value.trim()) {
            $field.addClass('error');
            return false;
        }
        
        // Check date formats
        if (fieldName.includes('data_') && value) {
            const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
            if (!dateRegex.test(value)) {
                $field.addClass('error');
                return false;
            }
        }
        
        return true;
    }
    
    checkIfProductStillModified($row) {
        const $modifiedFields = $row.find('.editable.modified');
        
        if ($modifiedFields.length === 0) {
            $row.removeClass('modified');
            this.hideRowActions($row);
            this.modifiedProducts.delete($row.data('product-id'));
        }
        
        this.updateSaveButtonState();
    }
    
    showRowActions($row) {
        $row.find('.save-btn, .undo-btn').show();
    }
    
    hideRowActions($row) {
        $row.find('.save-btn, .undo-btn').hide();
    }
    
    updateSaveButtonState() {
        const hasModified = this.modifiedProducts.size > 0;
        $('#save-all-btn').prop('disabled', !hasModified);
        
        if (hasModified) {
            $('#modified-count').text(`${this.modifiedProducts.size} modified`).show();
        } else {
            $('#modified-count').hide();
        }
    }
    
    // Save Methods
    saveProduct(event) {
        const $button = $(event.currentTarget);
        const $row = $button.closest('.product-row');
        const productId = $row.data('product-id');
        
        this.performSave([productId]);
    }
    
    undoProduct(event) {
        const $button = $(event.currentTarget);
        const $row = $button.closest('.product-row');
        const productId = $row.data('product-id');
        
        // Restore original values
        $row.find('.editable.modified').each((index, element) => {
            const $field = $(element);
            const originalValue = $field.data('original') || '';
            $field.val(originalValue).removeClass('modified error');
        });
        
        $row.removeClass('modified');
        this.hideRowActions($row);
        this.modifiedProducts.delete(productId);
        this.updateSaveButtonState();
    }
    
    saveAllModified() {
        if (this.modifiedProducts.size === 0) {
            return;
        }
        
        this.performSave(Array.from(this.modifiedProducts));
    }
    
    performSave(productIds) {
        const saveData = this.collectSaveData(productIds);
        
        // Mark products as saving
        productIds.forEach(id => {
            this.savingProducts.add(id);
            $(`.product-row[data-product-id="${id}"]`).addClass('saving');
        });
        
        $.ajax({
            url: '/api/products/save/',
            method: 'POST',
            headers: {
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val(),
                'Content-Type': 'application/json'
            },
            data: JSON.stringify({
                products: saveData
            }),
            success: (response) => {
                this.handleSaveSuccess(productIds, response);
            },
            error: (xhr, status, error) => {
                this.handleSaveError(productIds, error);
            }
        });
    }
    
    collectSaveData(productIds) {
        const saveData = [];
        
        productIds.forEach(productId => {
            const $row = $(`.product-row[data-product-id="${productId}"]`);
            const productData = { id: productId };
            
            // Collect modified fields
            $row.find('.editable.modified').each((index, element) => {
                const $field = $(element);
                const fieldName = $field.data('field');
                const value = $field.val();
                productData[fieldName] = value;
            });
            
            if (Object.keys(productData).length > 1) { // More than just ID
                saveData.push(productData);
            }
        });
        
        return saveData;
    }
    
    handleSaveSuccess(productIds, response) {
        // Remove saving state
        productIds.forEach(id => {
            this.savingProducts.delete(id);
            const $row = $(`.product-row[data-product-id="${id}"]`);
            $row.removeClass('saving modified');
            
            // Update original values
            $row.find('.editable').each((index, element) => {
                const $field = $(element);
                $field.removeClass('modified error');
                $field.data('original', $field.val());
            });
            
            this.hideRowActions($row);
            this.modifiedProducts.delete(id);
        });
        
        this.updateSaveButtonState();
        this.showSuccess(`Successfully saved ${productIds.length} product(s)`);
    }
    
    handleSaveError(productIds, error) {
        // Remove saving state
        productIds.forEach(id => {
            this.savingProducts.delete(id);
            $(`.product-row[data-product-id="${id}"]`).removeClass('saving');
        });
        
        this.showError('Failed to save changes: ' + error);
    }
    
    // Country Modal Methods
    openCountryModal(event) {
        event.preventDefault();
        const productId = $(event.currentTarget).data('product-id');
        
        // Load country data for this product
        this.loadCountryData(productId);

        // Unbind and rebind modal-specific events to avoid multiple bindings
        $('#country-search').off('input').on('input', this.debounce(this.searchCountries.bind(this), 200));
        $('#clear-search').off('click').on('click', () => {
            $('#country-search').val('').trigger('input');
        });
        $('#set-all-available').off('click').on('click', this.setAllCountries.bind(this, 'available'));
        $('#set-all-aap').off('click').on('click', this.setAllCountries.bind(this, 'as_available'));
        $('#clear-all').off('click').on('click', this.setAllCountries.bind(this, 'not_available'));
        $('[name="country-filter"]').off('change').on('change', this.filterCountries.bind(this));
        $('#reset-country-filter').off('click').on('click', this.resetCountryFilters.bind(this));
        $('#apply-visibility-rules, #auto-apply-rule').off('click').on('click', this.applyVisibilityRules.bind(this));
    }
    
    loadCountryData(productId) {
        $('#country-modal').find('.modal-title').text(`Edit Countries for Product ${productId} `);
        $('#country-modal').data('product-id', productId);
        
        // Load country data via AJAX
        $.ajax({
            url: `/api/products/${productId}/`,
            method: 'GET',
            success: (response) => {
                const product = response.product;
                
                // Update product info in the modal
                $('#product-sku').text(product.sku || productId);
                $('#product-visibility-rule').text(product.ecommerce_visibility || 'No rule set');
                
                // Show product info if there's a visibility rule
                if (product.ecommerce_visibility) {
                    $('#product-info-alert').show();
                } else {
                    $('#product-info-alert').hide();
                }
                
                this.renderCountryGrid(product.countries || []);
            },
            error: (xhr, status, error) => {
                this.showError('Failed to load country data: ' + error);
            }
        });
    }
    
    renderCountryGrid(countries) {
        // Organize countries by regions
        const countryRegions = {
            europe: {
                name: 'Europe',
                countries: ['AL', 'AT', 'BA', 'BE', 'BG', 'BY', 'CH', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MD', 'MK', 'MT', 'NL', 'PL', 'PT', 'RO', 'RS', 'RU', 'SE', 'SI', 'SK', 'UA', 'UK', 'XK']
            },
            asia: {
                name: 'Asia & Middle East',
                countries: ['AM', 'AZ', 'BH', 'CN', 'GE', 'HK', 'IL', 'JO', 'JP', 'KW', 'KZ', 'LB', 'MO', 'QA', 'SA', 'TN', 'TR', 'TW', 'UZ']
            },
            americas: {
                name: 'Americas',
                countries: ['BR', 'CO', 'MX', 'US']
            },
            others: {
                name: 'Others',
                countries: ['MA']
            }
        };
        
        const countryMap = {};
        countries.forEach(country => {
            countryMap[country.code] = country;
        });
        
        // Render each region
        Object.keys(countryRegions).forEach(regionKey => {
            const region = countryRegions[regionKey];
            let regionHtml = '';
            
            region.countries.forEach(code => {
                const country = countryMap[code] || { code: code, type: 'not_available', date: null };
                const countryName = this.getCountryName(code);
                
                regionHtml += `
                    <div class="col-md-4 col-lg-3 country-grid-item" data-country-code="${code}" data-country-name="${countryName}">
                        <div class="card h-100">
                            <div class="card-body p-2">
                                <h6 class="card-title mb-1">
                                    <span class="country-flag">${this.getCountryFlag(code)}</span>
                                    ${code}
                                    <small class="text-muted">${countryName}</small>
                                </h6>
                                <select class="form-select form-select-sm country-type mb-1" data-country="${code}">
                                    <option value="not_available" ${country.type === 'not_available' || !country.type ? 'selected' : ''}>❌ Not Available</option>
                                    <option value="available" ${country.type === 'available' ? 'selected' : ''}>✅ Available</option>
                                    <option value="as_available" ${country.type === 'as_available' ? 'selected' : ''}>⏳ AAP</option>
                                    <option value="data_specifica" ${country.type === 'data_specifica' ? 'selected' : ''}>📅 Specific Date</option>
                                </select>
                                <input type="date" class="form-control form-control-sm country-date" 
                                       data-country="${code}"
                                       value="${country.date || ''}"
                                       ${country.type !== 'data_specifica' ? 'style="display: none;"' : ''} />
                            </div>
                        </div>
                    </div>
                `;// AAP As Available
            });
            
            $(`#${regionKey}-grid`).html(regionHtml);
        });
        
        // Bind events for country type changes
        $('.country-type').on('change', function() {
            const $select = $(this);
            const $dateInput = $select.siblings('.country-date');
            
            if ($select.val() === 'data_specifica') {
                $dateInput.show().focus();
            } else {
                $dateInput.hide().val('');
            }
            
            // Update counters
            this.updateCountryCounts();
        }.bind(this));
        
        $('.country-date').on('change', function() {
            this.updateCountryCounts();
        }.bind(this));
        
        // Initial count update
        this.updateCountryCounts();
    }
    
    getCountryName(code) {
        const countryNames = {
            'AL': 'Albania', 'AM': 'Armenia', 'AT': 'Austria', 'AZ': 'Azerbaijan', 'BA': 'Bosnia',
            'BE': 'Belgium', 'BG': 'Bulgaria', 'BH': 'Bahrain', 'BR': 'Brazil', 'BY': 'Belarus',
            'CH': 'Switzerland', 'CN': 'China', 'CO': 'Colombia', 'CY': 'Cyprus', 'CZ': 'Czech Republic',
            'DE': 'Germany', 'DK': 'Denmark', 'EE': 'Estonia', 'ES': 'Spain', 'FL': 'Liechtenstein',
            'FR': 'France', 'GB': 'United Kingdom', 'GE': 'Georgia', 'GR': 'Greece', 'HK': 'Hong Kong',
            'HR': 'Croatia', 'HU': 'Hungary', 'IE': 'Ireland', 'IL': 'Israel', 'IT': 'Italy',
            'JO': 'Jordan', 'JP': 'Japan', 'KW': 'Kuwait', 'KZ': 'Kazakhstan', 'LB': 'Lebanon',
            'LT': 'Lithuania', 'LU': 'Luxembourg', 'LV': 'Latvia', 'MA': 'Morocco', 'MD': 'Moldova',
            'MK': 'North Macedonia', 'MO': 'Macao', 'MT': 'Malta', 'MX': 'Mexico', 'NL': 'Netherlands',
            'PL': 'Poland', 'PT': 'Portugal', 'QA': 'Qatar', 'RO': 'Romania', 'RS': 'Serbia',
            'RU': 'Russia', 'SA': 'Saudi Arabia', 'SE': 'Sweden', 'SI': 'Slovenia', 'SK': 'Slovakia',
            'TN': 'Tunisia', 'TR': 'Turkey', 'TW': 'Taiwan', 'UA': 'Ukraine', 'UK': 'United Kingdom',
            'US': 'United States', 'UZ': 'Uzbekistan', 'XK': 'Kosovo'
        };
        return countryNames[code] || code;
    }
    
    getCountryFlag(code) {
        // Use flag-icons library for cross-browser compatibility
        let flagCode = code.toLowerCase();
        const specialCases = {
            'uk': 'gb', // Use 'gb' for United Kingdom
            'fl': 'li'  // Use 'li' for Liechtenstein
        };

        if (specialCases[flagCode]) {
            flagCode = specialCases[flagCode];
        }

        // Return an img tag pointing to the flag icon SVG
        return `<img src="https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.2.2/flags/4x3/${flagCode}.svg" 
                     alt="${code}" 
                     style="width: 1.33em; height: 1em; vertical-align: middle;">`;
    }
    
    updateCountryCounts() {
        let availableCount = 0;
        let aapCount = 0;
        let dateCount = 0;
        
        $('.country-type').each(function() {
            const value = $(this).val();
            if (value === 'available') availableCount++;
            else if (value === 'as_available') aapCount++;
            else if (value === 'data_specifica') dateCount++;
        });
        
        $('#available-count').text(availableCount);
        $('#aap-count').text(aapCount);
        $('#date-count').text(dateCount);
    }
    
    searchCountries(event) {
        const searchTerm = event.target.value.toLowerCase();
        
        $('.country-grid-item').each(function() {
            const $item = $(this);
            const countryCode = $item.data('country-code').toLowerCase();
            const countryName = $item.data('country-name').toLowerCase();
            
            const matches = countryCode.includes(searchTerm) || 
                          countryName.includes(searchTerm) ||
                          searchTerm === '';
            
            $item.toggle(matches);
        });
    }
    
    setAllCountries(type) {
        const $visibleCountries = $('.country-grid-item:visible .country-type');
        $visibleCountries.val(type).trigger('change');
        this.showSuccess(`Set ${$visibleCountries.length} countries to ${type.replace('_', ' ')}`);
    }
    
    filterCountries(event) {
        const filterValue = $(event.currentTarget).val();
        $('#reset-country-filter').show();

        $('.country-grid-item').each(function() {
            const $item = $(this);
            const countryType = $item.find('.country-type').val();
            let show = false;

            if (filterValue === 'available' && (countryType === 'available' || countryType === 'data_specifica')) {
                show = true;
            } else if (filterValue === 'not-available' && countryType === 'not_available') {
                show = true;
            } else if (filterValue === 'aap' && countryType === 'as_available') {
                show = true;
            }

            $item.toggle(show);
        });
    }

    resetCountryFilters() {
        // Uncheck all radio buttons
        $('[name="country-filter"]').prop('checked', false);
        // Show all country items
        $('.country-grid-item').show();
        // Hide the reset button
        $('#reset-country-filter').hide();
    }

    saveCountries() {
        const productId = $('#country-modal').data('product-id');
        const countries = [];
        
        $('.country-type').each((index, element) => {
            const $select = $(element);
            const code = $select.data('country');
            const type = $select.val();
            const date = $select.siblings('.country-date').val();
            
            countries.push({
                code: code,
                type: type,
                date: date || null
            });
        });
        
        // Save via API
        $.ajax({
            url: '/api/products/save/',
            method: 'POST',
            headers: {
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val(),
                'Content-Type': 'application/json'
            },
            data: JSON.stringify({
                products: [{
                    id: productId,
                    countries: countries
                }]
            }),
            success: (response) => {
                $('#country-modal').modal('hide');
                this.showSuccess('Countries updated successfully');
                // Refresh the row to show updated countries
                this.refreshProductRow(productId);
            },
            error: (xhr, status, error) => {
                this.showError('Failed to save countries: ' + error);
            }
        });
    }
    
    refreshProductRow(productId) {
        // Reload just this product row
        $.ajax({
            url: window.location.pathname,
            method: 'GET',
            data: { 
                product_id: productId,
                single_row: true 
            },
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: (response) => {
                if (response.html) {
                    $(`.product-row[data-product-id="${productId}"]`).replaceWith(response.html);
                }
            }
        });
    }
    
    applyVisibilityRules() {
        console.log('🚀 applyVisibilityRules called');
        const productId = $('#country-modal').data('product-id');
        console.log('📦 Product ID:', productId);
        
        if (!productId) {
            console.error('❌ No product ID found');
            this.showError('No product selected');
            return;
        }
        
        // Show loading state
        const $button = $('#apply-visibility-rules, #auto-apply-rule');
        const originalText = $button.first().html();
        console.log('🔄 Setting loading state...');
        $button.html('<i class="bi bi-hourglass-split"></i> Applying...').prop('disabled', true);
        
        // Get CSRF token
        const csrfToken = $('[name=csrfmiddlewaretoken]').val();
        console.log('🔐 CSRF Token:', csrfToken ? 'Found' : 'Missing!');
        
        const url = `/api/products/${productId}/apply-visibility-rules/`;
        console.log('🌐 API URL:', url);
        
        // Apply visibility rules via API
        $.ajax({
            url: url,
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            success: (response) => {
                console.log('✅ Success response:', response);
                this.showSuccess(response.message);
                
                // Reload the country data to show updated countries
                this.loadCountryData(productId);
                
                // Show applied rule info
                if (response.rule_applied) {
                    $('#product-visibility-rule').text(response.rule_applied);
                    $('#product-info-alert').show();
                }
            },
            error: (xhr, status, error) => {
                console.error('❌ Error response:', xhr.responseJSON);
                console.error('❌ Status:', status);
                console.error('❌ Error:', error);
                const errorMsg = xhr.responseJSON?.message || error;
                this.showError('Failed to apply visibility rules: ' + errorMsg);
            },
            complete: () => {
                console.log('🏁 Request completed');
                // Restore button state
                $button.html(originalText).prop('disabled', false);
            }
        });
    }
    
    // Bulk Operations
    showBulkOperationsButton() {
        if (!$('#bulk-operations-btn').length) {
            const $button = $(`
                <button id="bulk-operations-btn" class="btn btn-info btn-sm" data-bs-toggle="modal" data-bs-target="#bulk-modal">
                    <i class="bi bi-gear"></i> Bulk Edit
                </button>
            `);
            $('.header-bar .btn-group').prepend($button);
        }
    }
    
    hideBulkOperationsButton() {
        $('#bulk-operations-btn').remove();
    }
    
    applyBulkChanges() {
        const selectedIds = Array.from(this.selectedProducts);
        
        if (selectedIds.length === 0) {
            this.showError('No products selected');
            return;
        }
        
        const bulkData = {
            fornitore: $('#bulk-supplier').val(),
            made_in: $('#bulk-made-in').val(),
            serie: $('#bulk-series').val()
        };
        
        // Remove empty values
        Object.keys(bulkData).forEach(key => {
            if (!bulkData[key]) delete bulkData[key];
        });
        
        if (Object.keys(bulkData).length === 0) {
            this.showError('No changes to apply');
            return;
        }
        
        // Apply changes to selected products
        selectedIds.forEach(productId => {
            const $row = $(`.product-row[data-product-id="${productId}"]`);
            
            Object.keys(bulkData).forEach(field => {
                const value = bulkData[field];
                const $field = $row.find(`[data-field="${field}"]`);
                if ($field.length) {
                    $field.val(value).trigger('input');
                }
            });
        });
        
        $('#bulk-modal').modal('hide');
        this.showSuccess(`Applied bulk changes to ${selectedIds.length} products`);
        
        // Clear form
        $('#bulk-supplier, #bulk-made-in, #bulk-series').val('');
    }
    
    // Utility Methods
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'danger');
    }
    
    showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        // Add toast container if it doesn't exist
        if (!$('.toast-container').length) {
            $('body').append('<div class="toast-container position-fixed top-0 end-0 p-3"></div>');
        }
        
        const $toast = $(toastHtml);
        $('.toast-container').append($toast);
        
        const toast = new bootstrap.Toast($toast[0]);
        toast.show();
        
        // Remove toast element after it's hidden
        $toast.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }
}

// Initialize when document is ready
$(document).ready(function() {
    console.log('🚀 Initializing ModernTableView...');
    window.modernTableView = new ModernTableView();
    console.log('✅ ModernTableView initialized successfully');
});

// Fallback check if jQuery is not loaded
if (typeof $ === 'undefined') {
    console.error('❌ jQuery is not loaded! Please include jQuery before this script.');
    alert('Error: jQuery is required for this page to function properly.');
}
